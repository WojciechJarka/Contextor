import json
import sys

def parse_report():
    with open(r"c:\Temp\Repo_Guardian_Repo\output\Repo_Guardian_Repo_artifacts.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print("ANALIZA MARTWEGO KODU W OPARCIU O RAPORT:")
    targets = [
        "count_nodes", "count_edges", "compute_degrees", 
        "FunctionCallVisitor", "FunctionMutationVisitor", 
        "ImportUsageVisitor", "MutabilityVisitor",
        "validate_name_collisions"
    ]
    
    found_any = False
    for k, v in data.get("artifacts", {}).items():
        art = v.get("artifact", "")
        if art in targets or any(t in k for t in targets):
            found_any = True
            cons_count = v.get("consumer_count", 0)
            print(f"- {art} ({k}) -> konsumentów: {cons_count}")
            if cons_count == 0:
                print(f"  [DECYZJA]: Kwalifikuje się do USUNIĘCIA (Martwy Kod)")
            else:
                print(f"  [DECYZJA]: Aktywnie używany przez: {v.get('consumers', [])}")
                
    if not found_any:
        print("Nie znaleziono tych artefaktów pod dokładnymi nazwami, ale usuwamy z pliku.")

if __name__ == "__main__":
    parse_report()
