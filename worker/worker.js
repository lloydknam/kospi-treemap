// GitHub Actions 예약 실행이 몇 시간씩 밀리는 문제를 피하기 위한 정시 트리거.
// Cloudflare Cron이 정해진 시각에 kospi-treemap 워크플로를 직접 실행한다.
// force=false: 새 거래일·지수 값이 없으면 배포·영상 생성을 건너뛴다 (휴장일·중복 실행 안전).
const REPO = "lloydknam/kospi-treemap";
const WORKFLOW = "treemap.yml";

async function dispatch(env, fetchImpl = fetch) {
  if (!env.GH_TOKEN) throw new Error("GH_TOKEN secret is not set");
  const res = await fetchImpl(
    `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GH_TOKEN}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "kospi-trigger",
      },
      body: JSON.stringify({ ref: "main", inputs: { force: "false" } }),
    },
  );
  if (res.status !== 204) {
    // 실패를 던져야 Cloudflare Cron 이벤트 기록에 실패로 남는다
    throw new Error(`dispatch failed: ${res.status} ${await res.text()}`);
  }
}

export default {
  async scheduled(_event, env) {
    await dispatch(env);
  },
  // 주소를 아는 사람이 임의로 실행할 수 없도록 HTTP 요청으로는 실행하지 않는다
  async fetch() {
    return new Response("kospi-trigger: cron only\n");
  },
};

export { dispatch };
