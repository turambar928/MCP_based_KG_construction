import os
import json
import argparse
import requests
from urllib.parse import urlencode

HEADERS = {"User-Agent": "env-fin-fetcher/1.0"}

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def save_jsonl(rows, path):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def rec(unid, service_item, power_type, actor, undertaker, basis, responsibilities, phone=""):
    return {
        "统一发布平台unid": str(unid) if unid is not None else "",
        "服务事项": service_item or "未提供",
        "权力类型": power_type or "",
        "行驶主体": actor or "",
        "承办机构": undertaker or "",
        "实施依据": basis or "",
        "责任事项": responsibilities or "",
        "监管电话": phone or ""
    }

# ============ 金融：CFPB消费者投诉（Socrata API: data.consumerfinance.gov） ============
# 资源ID：s6ew-h6mp
# 字段（常用）：complaint_id, product, issue, company, company_response, timely_response, consumer_disputed, date_received, state
def fetch_cfpb(limit=200, product=None, issue=None, company=None):
    base = "https://data.consumerfinance.gov/resource/s6ew-h6mp.json"
    params = {
        "$limit": limit if limit and limit > 0 else 5000,
        "$order": "date_received DESC"
    }
    where = []
    if product:
        where.append(f"upper(product)=upper('{product}')")
    if issue:
        where.append(f"upper(issue)=upper('{issue}')")
    if company:
        where.append(f"upper(company)=upper('{company}')")
    if where:
        params["$where"] = " AND ".join(where)

    resp = requests.get(base, params=params, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    rows = []
    for x in data:
        complaint_id = x.get("complaint_id")
        product = x.get("product", "")
        issue = x.get("issue", "")
        company = x.get("company", "")
        company_resp = x.get("company_response", "")
        timely = x.get("timely_response", "")
        disputed = x.get("consumer_disputed", "")
        date = x.get("date_received", "")
        state = x.get("state", "")

        # 映射
        service_item = f"{product} - {issue}".strip(" -")
        power_type = "金融投诉"
        actor = company or "未披露机构"
        undertaker = "CFPB"
        # 实施依据：原始条目链接（Socrata数据行不可直链，这里给出查询URL）
        basis = f"{base}?{urlencode({'complaint_id': complaint_id})}" if complaint_id else base
        responsibilities = "\n".join([
            f"公司回复: {company_resp}" if company_resp else "",
            f"是否及时回复: {timely}" if timely else "",
            f"消费者是否异议: {disputed}" if disputed else "",
            f"接收日期: {date}" if date else "",
            f"州: {state}" if state else ""
        ]).strip()
        rows.append(rec(f"cfpb:{complaint_id}", service_item, power_type, actor, undertaker, basis, responsibilities))
    return rows

# ============ 环境：OpenAQ空气质量监测 ============
# API: https://api.openaq.org/v2/measurements
# 主要字段：id, parameter, value, unit, location, city, country, date.utc, coordinates(lat/lon), sourceName/entity
def fetch_openaq(limit=200, country=None, city=None, parameter=None):
    base = "https://api.openaq.org/v2/measurements"
    params = {
        "limit": limit if limit and limit > 0 else 1000,
        "sort": "desc",
        "order_by": "date"
    }
    if country:
        params["country"] = country
    if city:
        params["city"] = city
    if parameter:
        params["parameter"] = parameter

    resp = requests.get(base, params=params, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    js = resp.json()
    results = js.get("results", [])

    rows = []
    for r in results:
        mid = r.get("id")
        param = r.get("parameter", "")
        val = r.get("value", "")
        unit = r.get("unit", "")
        loc = r.get("location", "")
        cty = r.get("city", "")
        ctry = r.get("country", "")
        dt = (r.get("date") or {}).get("utc", "")
        coords = r.get("coordinates") or {}
        lat, lon = coords.get("latitude"), coords.get("longitude")
        source = r.get("sourceName") or r.get("entity") or "OpenAQ源"

        service_item = f"空气质量监测：{param}".strip()
        power_type = "环境监测通告"
        actor = loc or cty or ctry or "监测站点"
        undertaker = source
        # 实施依据：可回溯查询链接（带关键参数）
        q = {k: v for k, v in [("country", country), ("city", city), ("parameter", parameter)] if v}
        basis = f"{base}?{urlencode(q)}" if q else base
        responsibilities = "\n".join([
            f"监测值: {val} {unit}".strip(),
            f"时间(UTC): {dt}" if dt else "",
            f"位置: {loc} / {cty} / {ctry}".strip(" /"),
            f"坐标: {lat},{lon}" if (lat is not None and lon is not None) else ""
        ]).strip()
        rows.append(rec(f"openaq:{mid}", service_item, power_type, actor, undertaker, basis, responsibilities))
    return rows

def main():
    ap = argparse.ArgumentParser(description="抓取非政务数据（金融CFPB投诉 / 环境OpenAQ）并转为政务.jsonl同构JSONL")
    ap.add_argument("--sources", nargs="+", choices=["cfpb", "openaq", "all"], default=["all"])
    ap.add_argument("--limit", type=int, default=200, help="每来源条数（0为API上限）")

    # CFPB 过滤
    ap.add_argument("--cfpb-product", help="CFPB: 按产品过滤，如 'Credit card' 等")
    ap.add_argument("--cfpb-issue", help="CFPB: 按问题过滤，如 'Billing disputes' 等")
    ap.add_argument("--cfpb-company", help="CFPB: 按公司过滤")

    # OpenAQ 过滤
    ap.add_argument("--openaq-country", help="OpenAQ: 国家代码，如 CN/US/GB")
    ap.add_argument("--openaq-city", help="OpenAQ: 城市名（英文），如 Beijing")
    ap.add_argument("--openaq-parameter", help="OpenAQ: 监测项，如 pm25, pm10, o3, no2, so2, co")

    ap.add_argument("--out-dir", default=os.path.join("data", "non_gov_jsonl"), help="输出目录")
    ap.add_argument("--combined-output", default=os.path.join("data", "non_gov_jsonl", "combined_env_fin.jsonl"))
    args = ap.parse_args()

    ensure_dir(args.out_dir)
    selected = ["cfpb", "openaq"] if "all" in args.sources else args.sources

    all_rows = []

    if "cfpb" in selected:
        rows = fetch_cfpb(
            limit=None if args.limit == 0 else args.limit,
            product=args.cfpb_product,
            issue=args.cfpb_issue,
            company=args.cfpb_company
        )
        p = os.path.join(args.out_dir, "cfpb.jsonl")
        save_jsonl(rows, p)
        all_rows.extend(rows)
        print(f"CFPB: {len(rows)} -> {p}")

    if "openaq" in selected:
        rows = fetch_openaq(
            limit=None if args.limit == 0 else args.limit,
            country=args.openaq_country,
            city=args.openaq_city,
            parameter=args.openaq_parameter
        )
        p = os.path.join(args.out_dir, "openaq.jsonl")
        save_jsonl(rows, p)
        all_rows.extend(rows)
        print(f"OpenAQ: {len(rows)} -> {p}")

    save_jsonl(all_rows, args.combined_output)
    print(f"合并输出: {len(all_rows)} -> {args.combined_output}")

if __name__ == "__main__":
    main()