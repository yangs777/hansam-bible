/* A single, unauthenticated public-status read; no account data or polling. */
(async()=>{
  const status=document.getElementById('deployment-status');
  const link=document.getElementById('deployment-link');
  const labels={queued:'검사·공개 대기',in_progress:'검사·공개 진행 중',waiting:'승인 대기',pending:'공개 대기',requested:'공개 요청됨'};
  const conclusions={success:'검사·배포 성공',failure:'검사·배포 실패',cancelled:'공개 작업 취소',timed_out:'공개 작업 시간 초과',action_required:'확인 필요',skipped:'공개 작업 건너뜀',neutral:'공개 작업 종료'};
  try{
    const response=await fetch('https://api.github.com/repos/yangs777/hansam-bible/actions/workflows/pages.yml/runs?branch=main&per_page=1',{credentials:'omit',signal:AbortSignal.timeout(8000)});
    if(!response.ok)throw new Error('Unavailable');
    const data=await response.json();const run=data.workflow_runs?.[0];
    if(!run)throw new Error('No public run');
    const label=run.status==='completed'?(conclusions[run.conclusion]||'공개 작업 종료'):(labels[run.status]||'공개 작업 진행 중');
    const date=new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',dateStyle:'medium',timeStyle:'short'}).format(new Date(run.updated_at));
    status.textContent=label+' · '+date+' KST (작업 상태 갱신 시각)';
    if(typeof run.html_url==='string'&&/^https:\/\/github\.com\/yangs777\/hansam-bible\/actions\/runs\/\d+$/.test(run.html_url))link.href=run.html_url;
  }catch(_){status.textContent='실시간 공개 상태를 불러오지 못했습니다. 아래 이력과 검사·배포 기록 링크를 확인해 주세요.';}
})();
