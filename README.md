# kospi-treemap
KOSPI 시총 트리맵 영상 자동 생성 (면적=시총, 색=등락률). Actions 탭에서 Run workflow, 결과는 Releases/latest.


## 인터랙티브 페이지 (GitHub Pages)
- `site/index.html` — 날짜 슬라이더·재생·툴팁·비중/절대 토글이 있는 트리맵 (데이터는 빌드 시 `site/data.json` 생성)
- 매 평일 18:30 KST 자동 갱신 (`build_web.py` → Pages 배포). 새 거래일이 없으면(휴장일) 배포·영상 생성을 건너뜀
- 최초 1회: Settings → Pages → Source 를 **GitHub Actions** 로 설정
- 실패 알림(선택): Secrets 에 `TG_BOT_TOKEN`, `TG_CHAT_ID` 를 넣으면 텔레그램으로 알림
