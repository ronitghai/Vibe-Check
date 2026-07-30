import { useState } from "react";
import { generatePracticeContent } from "../api/client";
import type { RecommendedActivityApi } from "../api/client";
import type { PlayingGame } from "../types";

interface Props { sessionId:string; recommendation:RecommendedActivityApi; onPlay:(game:PlayingGame,id:string,domain:string)=>void; }
export default function Az900RecommendationCard({sessionId,recommendation,onPlay}:Props){
 const [busy,setBusy]=useState(false); const [error,setError]=useState<string|null>(null);
 async function launch(){setBusy(true);setError(null);try{const r=await generatePracticeContent(sessionId,recommendation.gameId,recommendation.domain);onPlay({gameId:r.game_id,gameType:r.game_type as "template"|"generated"},r.game_id,r.domain);}catch{setError("Could not generate the recommended activity. Please try again.");}finally{setBusy(false)}}
 return <section className="recommendation-card"><div><div className="game-meta">Recommended next activity</div><h3>{recommendation.gameLabel}</h3><p><strong>{recommendation.domain}</strong> · {recommendation.difficulty} · {recommendation.masteryPct}% mastery</p><p>{recommendation.reason}</p>{error&&<p className="error">{error}</p>}</div><button className="btn" disabled={busy} onClick={launch}>{busy?"Preparing…":"Start recommendation"}</button></section>;
}
