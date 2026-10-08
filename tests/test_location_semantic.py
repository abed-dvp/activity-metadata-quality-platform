import pandas as pd
from src.evaluation.run_location_semantic import haversine_m, classify_distance, deterministic_sample

def test_distance_and_routing():
    assert haversine_m(51.5, -0.1, 51.5, -0.1) == 0
    assert classify_distance(100) == "consistent"
    assert classify_distance(800) == "uncertain"
    assert classify_distance(2000) == "suspicious"
    assert classify_distance(None) == "unresolved"

def test_sample_reproducible():
    df = pd.DataFrame({"entity_id":["a","b",None],"name":["A","B","C"],"address":["A St","B St","C St"],"latitude":[51.5]*3,"longitude":[-0.1]*3})
    assert deterministic_sample(df,2,42)["entity_id"].tolist() == deterministic_sample(df,2,42)["entity_id"].tolist()
