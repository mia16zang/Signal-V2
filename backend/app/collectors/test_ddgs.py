from duckduckgo_search import DDGS

print("starting")

with DDGS() as ddgs:
    print("inside")
    results = list(ddgs.text("AI Nutrition Coach", max_results=5))
    print("done")
    print(results)