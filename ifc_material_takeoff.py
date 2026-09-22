import json
import math
import os
import sys
from collections import defaultdict

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.unit


SKIP_CLASSES = {"IfcOpeningElement", "IfcVoidingFeature", "IfcProjectionElement"}
TARGET_CLASSES = ("IfcWall", "IfcWallStandardCase")


def _storey_name(element):
    storey = ifcopenshell.util.element.get_container(element, ifc_class="IfcBuildingStorey")
    return (getattr(storey, "Name", None) or getattr(storey, "LongName", None) or "층 미지정") if storey else "층 미지정"


def _quantity_volume(element, volume_scale):
    qtos = ifcopenshell.util.element.get_psets(element, qtos_only=True)
    candidates = []
    for qto in qtos.values():
        if not isinstance(qto, dict):
            continue
        for name, raw in qto.items():
            if name == "id" or "volume" not in name.lower() or not isinstance(raw, (int, float)):
                continue
            priority = 0 if "netvolume" in name.lower() else 1 if "grossvolume" in name.lower() else 2
            candidates.append((priority, float(raw)))
    if not candidates:
        return None
    volume = sorted(candidates)[0][1] * volume_scale
    return volume if math.isfinite(volume) and volume > 0 else None


def _geometry_volume(element, settings):
    try:
        shape = ifcopenshell.geom.create_shape(settings, element)
        verts = shape.geometry.verts
        faces = shape.geometry.faces
        signed = 0.0
        for i in range(0, len(faces), 3):
            ia, ib, ic = faces[i] * 3, faces[i + 1] * 3, faces[i + 2] * 3
            ax, ay, az = verts[ia:ia + 3]
            bx, by, bz = verts[ib:ib + 3]
            cx, cy, cz = verts[ic:ic + 3]
            signed += ax * (by * cz - bz * cy) + ay * (bz * cx - bx * cz) + az * (bx * cy - by * cx)
        volume = abs(signed) / 6.0
        return volume if math.isfinite(volume) and volume > 1e-9 else None
    except Exception:
        return None


def _material_parts(element):
    material = ifcopenshell.util.element.get_material(element, should_skip_usage=False)
    if material is None:
        return [("재료 미지정", 1.0, "unassigned")]
    if material.is_a("IfcMaterial"):
        return [(material.Name or "이름 없는 재료", 1.0, "single")]
    if material.is_a("IfcMaterialLayerSetUsage"):
        material = material.ForLayerSet
    if material.is_a("IfcMaterialLayerSet"):
        layers = list(material.MaterialLayers or [])
        total = sum(float(layer.LayerThickness or 0) for layer in layers)
        if total > 0:
            return [((layer.Material.Name if layer.Material else None) or "재료 미지정", float(layer.LayerThickness or 0) / total, "layer-thickness") for layer in layers if float(layer.LayerThickness or 0) > 0]
    materials = ifcopenshell.util.element.get_materials(element)
    if materials:
        share = 1.0 / len(materials)
        return [((m.Name or "이름 없는 재료"), share, "equal-share") for m in materials]
    return [(getattr(material, "Name", None) or material.is_a(), 1.0, "set")]


def analyze_ifc(ifc_path):
    model = ifcopenshell.open(ifc_path)
    try:
        volume_scale = ifcopenshell.util.unit.calculate_unit_scale(model, "VOLUMEUNIT")
    except Exception:
        volume_scale = ifcopenshell.util.unit.calculate_unit_scale(model, "LENGTHUNIT") ** 3
    settings = ifcopenshell.geom.settings()
    grouped = defaultdict(lambda: {"volume_m3": 0.0, "element_ids": set(), "quantity_elements": 0, "geometry_elements": 0})
    processed = 0
    skipped = 0
    # 공개 Render 인스턴스의 메모리를 보호하기 위해 재료 산출 대상인 벽만
    # 순회합니다. 전체 IfcElement의 형상 생성은 대형 IFC에서 프로세스를
    # 종료시킬 수 있고, 이 화면의 산출 목적과도 맞지 않습니다.
    elements = model.by_type("IfcWall")
    for element in elements:
        if element.is_a() in SKIP_CLASSES or element.is_a("IfcFeatureElement"):
            continue
        volume = _quantity_volume(element, volume_scale)
        method = "quantity"
        if volume is None:
            volume = _geometry_volume(element, settings)
            method = "geometry"
        if volume is None:
            skipped += 1
            continue
        processed += 1
        storey = _storey_name(element)
        for material_name, ratio, allocation in _material_parts(element):
            row = grouped[(storey, material_name, allocation)]
            row["volume_m3"] += volume * ratio
            row["element_ids"].add(element.GlobalId)
            row[f"{method}_elements"] += 1
    rows = []
    for (storey, material, allocation), data in grouped.items():
        rows.append({
            "storey": storey,
            "material": material,
            "volume_m3": round(data["volume_m3"], 6),
            "element_count": len(data["element_ids"]),
            "allocation": allocation,
            "quantity_elements": data["quantity_elements"],
            "geometry_elements": data["geometry_elements"],
        })
    rows.sort(key=lambda row: (row["storey"], row["material"]))
    return {"source": os.path.basename(ifc_path), "processed_elements": processed, "skipped_elements": skipped, "rows": rows}


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    result = analyze_ifc(args[0])
    print(json.dumps(result, ensure_ascii=False))
