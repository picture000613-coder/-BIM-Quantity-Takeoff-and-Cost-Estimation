# BIM Quantity Takeoff and Cost Estimation

GitHub Pages용 BIM IFC 브라우저 뷰어입니다.

## 현재 기능

- 브라우저에서 IFC 파일 열기
- 3D 모델 회전·확대·축소
- 층·이름·재료·IFC 형식으로 묶인 3D 레이어 목록
- 레이어별 표시·숨김과 전체 표시·전체 숨김
- 층별 재료 체적·단가·재료비 화면
- 콘크리트·유리·금속·목재·벽돌 등 재료군별 일괄단가 적용
- 전체 불러오기 상태 초기화
- 향후 SketchUp·Rhino 연동을 위한 UI 버튼
- Web-IFC JS/WASM을 저장소에 포함해 CDN WASM 404 방지

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
