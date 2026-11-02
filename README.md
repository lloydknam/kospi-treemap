# kospi-treemap
KOSPI 시총 트리맵 영상 자동 생성 (면적=시총, 색=등락률). Actions 탭에서 Run workflow, 결과는 Releases/latest.


## 인터랙티브 페이지 (GitHub Pages)
- `site/index.html` — 날짜 슬라이더·재생·툴팁·비중/절대 토글이 있는 트리맵 (데이터는 빌드 시 `site/data.json` 생성)
- 매 평일 16:40·20:35 KST 자동 갱신 (Cloudflare Worker → `build_web.py` → Pages 배포). 새 거래일이 없으면(휴장일) 배포·영상 생성을 건너뜀
- GitHub 예약 실행은 수 시간씩 밀려서 백업으로만 둠. 정시 실행은 `worker/`의 `kospi-trigger`가 맡음
- 최초 1회: Settings → Pages → Source 를 **GitHub Actions** 로 설정
- 실패 알림(선택): Secrets 에 `TG_BOT_TOKEN`, `TG_CHAT_ID` 를 넣으면 텔레그램으로 알림

## 정시 트리거 설치 (Cloudflare Worker, 무료)
1. GitHub → Settings → Developer settings → Fine-grained tokens: 저장소 `kospi-treemap`만 선택, 권한 `Actions: Read and write`
2. Cloudflare → Workers & Pages → Create → Hello World → 이름 `kospi-trigger` → Deploy → Edit code → `worker/worker.js` 붙여넣고 Deploy
3. Worker → Settings → Variables and Secrets → Secret `GH_TOKEN` 에 1번 토큰 등록
4. Worker → Settings → Trigger Events → Cron 두 개 추가: `40 7 * * mon-fri`, `35 11 * * mon-fri` (UTC)

토큰이 만료되면 수 시간 늦는 GitHub 예약으로 돌아가므로, 만료 전에 3번 값을 새 토큰으로 교체.
