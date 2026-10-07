import requests

def search_web(query):
    print(f"Searchin the web for : {query}")
    

    response = requests.get(
        "http://localhost:8080/search",
        params = {
            "q" : query,
            "format": "json"
        }
    )
    response.raise_for_status()
    
    data = response.json()
    
    results = []
    
    for result in data["results"][:3]:
        
        results.append({
            "title" : result["title"],
            "url" : result["url"],
            "content" : result.get("content","")[:350]
        })
        
    return str(results)

