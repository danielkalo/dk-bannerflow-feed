import csv, json, os, requests

API_URL  = "https://api.draftkings.com/ads/v1/ads/7341a429-d59e-11ee-945d-0ef9c4d3a02d.json"
GAMETYPE = "Slots"
USER = os.environ["DK_API_USERNAME"]
PASS = os.environ["DK_API_PASSWORD"]

def fetch(operator_code):
    r = requests.get(
        API_URL,
        params={"GameType": GAMETYPE, "Operator": operator_code},
        auth=(USER, PASS),
        timeout=180
    )
    r.raise_for_status()
    data = r.json().get("data", [])
    out = []
    for it in data:
        provider = str(it.get("ProviderId") or it.get("ContentProviderName") or "").strip()
        if not provider.lower().startswith("draftkings"):  # includes DraftKings2
            continue
        op = it.get("Operator") or {}
        op_code = op.get("Code") if isinstance(op, dict) else None
        op_code = op_code or operator_code

        def pick_image(v):
            if isinstance(v, list) and v:
                first = v[0]
                if isinstance(first, dict):
                    for k in ("Url","URL","url","LargeUrl","MainUrl","main","src"):
                        if first.get(k): return str(first[k])
                return json.dumps(v, separators=(",",":"))
            if isinstance(v, dict):
                for k in ("Url","URL","url","LargeUrl","MainUrl","main","src"):
                    if v.get(k): return str(v[k])
                return json.dumps(v, separators=(",",":"))
            return str(v) if v else ""

        row = {
            "GameName":      it.get("GameName") or it.get("Name") or it.get("Title") or "",
            "GameTypeId":    it.get("GameTypeId") or GAMETYPE,
            "Images":        pick_image(it.get("Images")),
            "Operator/Code": op_code,
            "ProviderId":    provider,
        }
        out.append(row)
    return out

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["GameName","GameTypeId","Images","Operator/Code","ProviderId"])
        w.writeheader()
        w.writerows(rows)

if __name__ == "__main__":
    # write files into repo root
    write_csv("games_dk.csv",   fetch("DK"))
    write_csv("games_gnog.csv", fetch("GNOG"))
