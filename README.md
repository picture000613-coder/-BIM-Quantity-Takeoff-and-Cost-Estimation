# BIM Quantity Takeoff and Cost Estimation

GitHub Pages용 IFC·SketchUp 물량산출 브라우저 뷰어입니다.

## 현재 기능

- 브라우저에서 IFC 파일 열기
- 브라우저에서 SketchUp `.skp` 파일 직접 열기
- 3D 모델 회전·확대·축소
- 층·이름·재료·IFC 형식으로 묶인 3D 레이어 목록
- SketchUp Tag별 객체 수, 닫힌 형상 수, 열린 형상 수, 체적·면적 합계
- 닫힌 형상은 체적(m³), 열린 형상은 삼각형 면적(m²)으로 분리 산출
- 레이어별 표시·숨김과 전체 표시·전체 숨김
- IFC 재료별 또는 SketchUp Tag별 체적·단가·비용 화면
- 콘크리트·유리·금속·목재·벽돌 등 재료군별 일괄단가 적용
- 전체 불러오기 상태 초기화
- 향후 Rhino 연동을 위한 UI 버튼
- Web-IFC JS/WASM을 저장소에 포함해 CDN WASM 404 방지

## SketchUp 분석

SketchUp 파일은 브라우저에서 [OpenSKP 1.3.0](https://github.com/iamahsanmehmood/openskp)으로 분석합니다. 파일 자체는 별도 서버로 업로드하지 않습니다.

- 그룹·컴포넌트 경로별로 여러 재질의 메시를 다시 합친 뒤 폐합 여부를 검사합니다.
- 모든 삼각형 모서리가 정확히 두 번 사용된 객체를 닫힌 형상으로 판정합니다.
- 닫힌 형상은 부호 있는 사면체 체적을 합산해 m³로 표시합니다.
- 열린 형상은 체적 대신 실제 삼각형 면적 합계를 m²로 산출하며 별도 면적 단가를 적용할 수 있습니다.
- 닫힌 형상 체적과 열린 형상 면적은 단위가 다르므로 각각 별도의 견적 행으로 표시합니다.
- 오래된 일부 SKP 버전이나 손상된 파일은 OpenSKP가 읽지 못할 수 있습니다. 큰 모델은 브라우저 메모리 한도의 영향을 받습니다.

## GitHub Pages

`main` 브랜치에 push하면 Pages workflow가 정적 뷰어를 배포합니다. 저장소 Settings → Pages에서 GitHub Actions 배포를 선택하세요.

## 재료 산출 API

GitHub Pages는 정적 호스팅이므로 IfcOpenShell을 실행할 수 없습니다. 공개 페이지에서 IFC 재료 체적을 자동 산출하려면 별도의 HTTPS API 서버가 필요합니다.

- API는 `POST /api/material-takeoff` 경로에서 IFC 바이너리를 받고 JSON 결과를 반환해야 합니다.
- 업로드는 임시 파일로 스트리밍되며 기본 최대 크기는 100MB입니다. QTO가 없는 벽은 제한된 범위에서 형상 체적으로 보완합니다.
- `bim_local_server.py`는 로컬 검증용 API이며 CORS 헤더가 포함되어 있습니다. 공개 배포 시에는 이 서버를 HTTPS가 되는 Python 호스팅에 배포하세요.
- 공개 뷰어에는 기본 API 주소 `https://bim-material-api.onrender.com`이 내부 설정으로 연결되어 있습니다. 사용자 화면에는 API 설정을 노출하지 않습니다. 무료 Render 서비스가 잠든 경우 첫 요청에 시간이 걸릴 수 있습니다.

서버 설정은 환경 변수 `MAX_UPLOAD_MB`(기본 100), `MAX_GEOMETRY_ELEMENTS`(기본 400), `ALLOW_GEOMETRY`로 조정할 수 있습니다.

### Render 배포

저장소의 `render.yaml`을 사용하면 Render에서 `bim-material-api` Web Service를 만들 수 있습니다. Render 대시보드에서 **New > Blueprint**를 선택하고 이 GitHub 저장소를 연결하면 됩니다. 배포가 끝나면 `https://<서비스명>.onrender.com`을 뷰어의 API 주소 입력란에 저장합니다. `/health`가 `{"status":"ok"}`를 반환하면 연결이 준비된 것입니다.
