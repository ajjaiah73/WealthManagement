from app.models import AdviceRequest
from app.compliance.solver import verify
def test_valid_draft_passes():
 r=AdviceRequest.model_validate({"client":{"client_id":"x","age":35,"annual_income":1,"liquid_assets":1,"risk_tolerance":"moderate","investment_horizon_years":10,"max_fee_pct":1},"goal":"long term investing","question":"What should I consider?"})
 d={"allocation":{"equity_pct":60,"bond_pct":30,"cash_pct":10},"recommendations":[{"product_id":"x","fee_pct":0.5,"source_ids":["s"]}]}
 assert all(x["passed"] for x in verify(r,d))
