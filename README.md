# BIM Quantity Takeoff and Cost Estimation

GitHub Pages용 BIM IFC 브라우저 뷰어입니다.

## 현재 기능

- 브라우저에서 IFC 파일 열기
- 3D 모델 회전·확대·축소
- JSON/CSV 벽 일람표 열기
- 층별 재료 체적·단가·재료비 화면
- Web-IFC JS/WASM을 저장소에 포함해 CDN WASM 404 방지

## GitHub Pages

`main` 브랜치에 push하면 Pages workflow가 정적 뷰어를 배포합니다. 저장소 Settings → Pages에서 GitHub Actions 배포를 선택하세요.

## 재료 산출 API

GitHub Pages는 정적 호스팅이므로 IfcOpenShell을 실행할 수 없습니다. 재료 체적 자동 산출을 사용하려면 별도의 HTTPS API 서버를 실행한 뒤 `index.html`의 `window.BIM_API_BASE`에 API 주소를 설정해야 합니다. API 구현 초안은 `bim_local_server.py`와 `ifc_material_takeoff.py`에 있습니다.

