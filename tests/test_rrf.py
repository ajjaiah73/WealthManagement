from app.retrieval.hybrid import rrf
def test_rrf_promotes_overlap():
 out=rrf([[{"id":"a"},{"id":"b"}],[{"id":"a"},{"id":"c"}]])
 assert out[0]["id"]=="a"
