from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pandas as pd
import json
import bcrypt
import os
from datetime import date, datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vinnie-dashboard-secret-2025")

DATA = os.path.join(os.path.dirname(__file__), "data")

# ── Password ──────────────────────────────────────────────────────────────────
PASSWORD_HASH = os.environ.get("PASSWORD_HASH", "")

def check_password(password):
    try:
        return bcrypt.checkpw(password.encode(), PASSWORD_HASH.encode())
    except:
        return False

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ── Data loaders ──────────────────────────────────────────────────────────────
def load_props():
    df = pd.read_csv(f"{DATA}/properties.csv")
    return df.to_dict("records")

def load_accounts():
    return pd.read_csv(f"{DATA}/accounts.csv").to_dict("records")

def load_cashflow():
    df = pd.read_csv(f"{DATA}/cashflow.csv")
    df["month"] = pd.to_datetime(df["month"]).dt.strftime("%b %Y")
    return df.to_dict("records")

def load_tenants():
    return pd.read_csv(f"{DATA}/tenants.csv").to_dict("records")

def load_lorries():
    return pd.read_csv(f"{DATA}/lorries.csv").to_dict("records")

def load_fuel():
    df = pd.read_csv(f"{DATA}/fuel.csv")
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%d %b")
    return df.to_dict("records")

def load_invoices():
    df = pd.read_csv(f"{DATA}/invoices.csv")
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%d %b")
    return df.to_dict("records")

def load_activity():
    try:
        df = pd.read_csv(f"{DATA}/activity_log.csv")
        df = df.where(pd.notnull(df), None)
        records = df.to_dict("records")
        return records[:8]
    except: return []

def log_activity(action, category, section, icon="📋"):
    try:
        from datetime import datetime
        import csv, os
        path = f"{DATA}/activity_log.csv"
        rows = []
        if os.path.exists(path):
            with open(path) as f:
                rows = list(csv.DictReader(f))
        rows.insert(0, {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "category": category,
            "section": section,
            "icon": icon
        })
        rows = rows[:50]  # keep last 50
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp","action","category","section","icon"])
            writer.writeheader()
            writer.writerows(rows)
    except: pass

def load_documents():
    try:
        df = pd.read_csv(f"{DATA}/documents.csv")
        df = df.where(pd.notnull(df), None)
        return df.to_dict("records")
    except: return []

def save_documents(records):
    pd.DataFrame(records).to_csv(f"{DATA}/documents.csv", index=False)

def load_problem_occupants():
    try:
        df = pd.read_csv(f"{DATA}/problem_occupants.csv")
        df = df.where(pd.notnull(df), None)
        records = df.to_dict("records")
        from datetime import date
        today = date.today()
        for r in records:
            if r.get("date_reported"):
                try:
                    reported = date.fromisoformat(str(r["date_reported"]))
                    r["days_since"] = (today - reported).days
                except: r["days_since"] = None
        return records
    except: return []

def save_problem_occupants(records):
    pd.DataFrame(records).to_csv(f"{DATA}/problem_occupants.csv", index=False)

def load_deposits():
    try:
        df = pd.read_csv(f"{DATA}/deposits.csv")
        df = df.where(pd.notnull(df), None)
        return df.to_dict("records")
    except: return []

def save_deposits(records):
    pd.DataFrame(records).to_csv(f"{DATA}/deposits.csv", index=False)

def load_vat_invoices():
    try:
        df = pd.read_csv(f"{DATA}/vat_invoices.csv")
        df = df.where(pd.notnull(df), None)
        return df.to_dict("records")
    except: return []

def save_vat_invoices(records):
    pd.DataFrame(records).to_csv(f"{DATA}/vat_invoices.csv", index=False)

def load_containers():
    try:
        df = pd.read_csv(f"{DATA}/containers.csv")
        return df.to_dict("records")
    except:
        return []

def save_containers(records):
    pd.DataFrame(records).to_csv(f"{DATA}/containers.csv", index=False)

def load_tasks():
    return pd.read_csv(f"{DATA}/tasks.csv").to_dict("records")

def save_tasks(tasks):
    pd.DataFrame(tasks).to_csv(f"{DATA}/tasks.csv", index=False)

def load_maint():
    return pd.read_csv(f"{DATA}/maintenance.csv").to_dict("records")

def save_maint(records):
    pd.DataFrame(records).to_csv(f"{DATA}/maintenance.csv", index=False)

def build_alerts(props, lorries, invoices):
    alerts = []
    today = date.today()
    for r in props:
        if r["rent_status"] == "Overdue":
            alerts.append({"level":"high","title":"Rent overdue","sub":r["address"],"icon":"🔴"})
        if r["rent_status"] == "Due":
            alerts.append({"level":"med","title":"Rent payment due","sub":r["address"],"icon":"⚠️"})
        if r["rent_status"] == "Vacant":
            alerts.append({"level":"med","title":"Vacant property","sub":f"{r['address']} — no income","icon":"🏚️"})
        end = r.get("tenancy_end","")
        if end and str(end) not in ["","nan"]:
            try:
                d = (pd.to_datetime(end).date() - today).days
                if 0 < d <= 60:
                    alerts.append({"level":"med","title":"Tenancy ending soon","sub":f"{r['address']} — {d} days","icon":"📅"})
            except: pass
        if r.get("mortgage_type") == "Tracker":
            alerts.append({"level":"low","title":"Tracker mortgage","sub":f"{r['address']} — monitor BoE rate","icon":"📈"})
    for r in lorries:
        try:
            d = (pd.to_datetime(r["mot_expiry"]).date() - today).days
            if d <= 60:
                alerts.append({"level":"high" if d<=30 else "med","title":"MOT expiring","sub":f"{r['reg']} — {d} days","icon":"🚛"})
        except: pass
    outstanding = [i for i in invoices if i["status"]=="Outstanding"]
    if outstanding:
        total = sum(float(i["amount_gbp"]) for i in outstanding)
        alerts.append({"level":"med","title":f"{len(outstanding)} unpaid invoices","sub":f"£{total:,.2f} outstanding","icon":"🧾"})
    return alerts

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("username","").lower() == "james" and check_password(request.form.get("password","")):
            session["authenticated"] = True
            return redirect(url_for("overview"))
        error = "Incorrect username or password."
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def overview():
    props     = load_props()
    accounts  = load_accounts()
    cashflow  = load_cashflow()
    lorries   = load_lorries()
    fuel      = load_fuel()
    invoices  = load_invoices()
    tasks     = load_tasks()

    occupied      = [p for p in props if p["rent_status"] != "Vacant"]
    total_rent    = sum(float(p["monthly_rent"]) for p in occupied if str(p.get("monthly_rent","")) not in ["","nan"])
    total_mtg     = sum(float(p["mortgage_monthly"]) for p in props)
    net_cf        = total_rent - total_mtg
    total_bal     = sum(float(a["balance"]) for a in accounts)
    total_fuel    = sum(float(f["cost_gbp"]) for f in fuel)
    total_vat     = sum(float(f["vat_gbp"]) for f in fuel)
    outstanding   = [i for i in invoices if i["status"]=="Outstanding"]
    out_total     = sum(float(i["amount_gbp"]) for i in outstanding)
    pending_tasks = [t for t in tasks if not t["done"]]
    recent_activity = load_activity()

    # Net worth
    property_values = {
        "5 Queensway Mildenhall": 550000,
        "5 Beeches Road West Row": 495000,
        "22 Fleming Avenue Mildenhall": 275000,
        "1 Bernards Close Mildenhall": 650000,
        "3 Bernards Close Mildenhall": 650000,
        "4 Bernards Close Mildenhall": 650000,
        "1A Vinrose Lodge Mildenhall": 160000,
        "5a Beeches Road West Row": 230000,
        "5b Beeches Road West Row": 230000,
        "Ponderosa West Row": 495000,
        "Ponderosa Annex West Row": 0,
        "St Michaels Thetford": 175000,
        "Garrod House Flat 1 Lakenheath": 125000,
        "Garrod House Flat 2 Lakenheath": 125000,
        "Garrod House Flat 3 Lakenheath": 125000,
        "Garrod House Flat B Lakenheath": 125000,
        "Sparks Farm Hurdle Drove": 900000,
        "Cottage Lakenheath": 175000,
        "Airview House West Row": 625000,
        "Airview Annex West Row": 0,
        "The Shed West Row": 275000,
    }
    total_property_value = sum(property_values.values())
    net_worth = total_property_value - total_mtg_bal if "total_mtg_bal" in dir() else total_property_value - 2019000

    # Rent collection this month
    paid_count    = len([p for p in props if p.get("rent_status") == "Paid"])
    overdue_count = len([p for p in props if p.get("rent_status") == "Overdue"])
    overdue_amount= sum(float(p.get("monthly_rent",0) or 0) for p in props if p.get("rent_status") == "Overdue")

    # Mortgage expiry alerts
    from datetime import date, datetime
    today = date.today()
    mortgage_alerts = []
    for p in props:
        me = p.get("mortgage_end")
        if me and str(me) not in ["","nan","None","SPT"]:
            try:
                end_date = datetime.strptime(str(me)[:10], "%Y-%m-%d").date()
                days_left = (end_date - today).days
                if days_left < 180:
                    mortgage_alerts.append({
                        "property": p["property"],
                        "end_date": str(me)[:10],
                        "days_left": days_left,
                        "lender": p.get("mortgage_lender",""),
                        "urgent": days_left < 60
                    })
            except: pass
    mortgage_alerts.sort(key=lambda x: x["days_left"])

    # Problem occupants summary
    problem_occ = load_problem_occupants()
    problem_count = len(problem_occ)
    problem_loss  = sum(float(o.get("estimated_loss_per_month",0) or 0) for o in problem_occ)
    alerts        = build_alerts(props, lorries, invoices)

    return render_template("overview.html",
        page="overview",
        props=props, accounts=accounts, cashflow=cashflow,
        occupied=occupied, total_rent=total_rent, total_mtg=total_mtg,
        net_cf=net_cf, total_bal=total_bal, total_fuel=total_fuel,
        total_vat=total_vat, out_total=out_total,
        pending_tasks=pending_tasks[:5], alerts=alerts,
        today=datetime.now().strftime("%A, %d %B %Y"),
        net_worth=net_worth,
        total_property_value=total_property_value,
        paid_count=paid_count,
        overdue_count=overdue_count,
        overdue_amount=overdue_amount,
        mortgage_alerts=mortgage_alerts,
        problem_count=problem_count,
        problem_loss=problem_loss,
        urgent_alerts=[a for a in alerts if a["level"]=="high"],
        recent_activity=recent_activity,
    )

@app.route("/properties")
@login_required
def properties():
    props   = load_props()
    occupied = [p for p in props if p["rent_status"] != "Vacant"]
    total_rent = sum(float(p["monthly_rent"]) for p in occupied if str(p.get("monthly_rent","")) not in ["","nan"])
    alerts = build_alerts(props, load_lorries(), load_invoices())
    return render_template("properties.html", page="properties", props=props,
        occupied=occupied, total_rent=total_rent, alerts=alerts)

@app.route("/property/<path:address>")
@login_required
def property_detail(address):
    props   = load_props()
    tenants = load_tenants()
    maint   = load_maint()
    prop    = next((p for p in props if p["address"] == address), None)
    if not prop: return redirect(url_for("properties"))
    tenant  = next((t for t in tenants if t["property"] == address), None)
    prop_maint = [m for m in maint if m["property"] == address]
    prop_maint.sort(key=lambda x: x["date"], reverse=True)
    days_left = None
    if tenant and str(tenant.get("tenancy_end","")) not in ["","nan"]:
        try: days_left = (pd.to_datetime(tenant["tenancy_end"]).date() - date.today()).days
        except: pass
    alerts = build_alerts(props, load_lorries(), load_invoices())
    return render_template("property_detail.html", page="properties",
        prop=prop, tenant=tenant, maint=prop_maint, days_left=days_left,
        alerts=alerts, address=address)

@app.route("/property/<path:address>/log_maint", methods=["POST"])
@login_required
def log_maint(address):
    maint = load_maint()
    maint.append({
        "property": address,
        "date": date.today().isoformat(),
        "issue": request.form["issue"],
        "status": request.form["status"],
        "cost": request.form.get("cost", 0),
        "notes": request.form.get("notes",""),
        "logged_by": "James"
    })
    save_maint(maint)
    return redirect(url_for("property_detail", address=address))

@app.route("/mortgages")
@login_required
def mortgages():
    props  = load_props()
    total_bal = sum(float(p["mortgage_balance"]) for p in props)
    total_mtg = sum(float(p["mortgage_monthly"]) for p in props)
    n_fixed   = len([p for p in props if p["mortgage_type"]=="Fixed"])
    n_tracker = len([p for p in props if p["mortgage_type"]=="Tracker"])
    alerts = build_alerts(props, load_lorries(), load_invoices())
    return render_template("mortgages.html", page="mortgages",
        props=props, total_bal=total_bal, total_mtg=total_mtg,
        n_fixed=n_fixed, n_tracker=n_tracker, alerts=alerts)

@app.route("/finance")
@login_required
def finance():
    props    = load_props()
    accounts = load_accounts()
    cashflow = load_cashflow()
    occupied = [p for p in props if p["rent_status"] != "Vacant"]
    total_rent = sum(float(p["monthly_rent"]) for p in occupied if str(p.get("monthly_rent","")) not in ["","nan"])
    total_mtg  = sum(float(p["mortgage_monthly"]) for p in props)
    net_cf     = total_rent - total_mtg
    total_bal  = sum(float(a["balance"]) for a in accounts)
    avg_net    = sum(float(c["net"]) for c in cashflow) / len(cashflow) if cashflow else 0
    forecast   = [(datetime.now()+timedelta(days=30*i)).strftime("%B %Y") for i in range(1,4)]
    alerts     = build_alerts(props, load_lorries(), load_invoices())
    return render_template("finance.html", page="finance",
        props=props, accounts=accounts, cashflow=cashflow,
        occupied=occupied, total_rent=total_rent, total_mtg=total_mtg,
        net_cf=net_cf, total_bal=total_bal, avg_net=avg_net,
        forecast=forecast, alerts=alerts)

@app.route("/lorries")
@login_required
def lorries():
    lorry_list = load_lorries()
    fuel       = load_fuel()
    invoices   = load_invoices()
    props      = load_props()
    total_fuel = sum(float(f["cost_gbp"]) for f in fuel)
    total_vat  = sum(float(f["vat_gbp"]) for f in fuel)
    outstanding= [i for i in invoices if i["status"]=="Outstanding"]
    out_total  = sum(float(i["amount_gbp"]) for i in outstanding)
    active     = len([l for l in lorry_list if l["status"]=="Active"])
    fuel_by_lorry = {}
    for f in fuel:
        reg = f["reg"]
        fuel_by_lorry[reg] = fuel_by_lorry.get(reg, 0) + float(f["cost_gbp"])
    alerts = build_alerts(props, lorry_list, invoices)
    return render_template("lorries.html", page="lorries",
        lorries=lorry_list, fuel=fuel, invoices=invoices[:6],
        container_income=container_income, container_vacant_loss=container_vacant_loss,
        lorry_income=lorry_income, fuel_costs=fuel_costs,
        combined_monthly=combined_monthly, combined_net=combined_net, daily_income=daily_income,
        total_fuel=total_fuel, total_vat=total_vat, out_total=out_total,
        active=active, fuel_by_lorry=fuel_by_lorry, alerts=alerts)

@app.route("/lorry/<lorry_id>")
@login_required
def lorry_detail(lorry_id):
    lorry_list = load_lorries()
    fuel       = load_fuel()
    invoices   = load_invoices()
    props      = load_props()
    lorry      = next((l for l in lorry_list if l["lorry_id"]==lorry_id), None)
    if not lorry: return redirect(url_for("lorries"))
    lf = [f for f in fuel if f["lorry_id"]==lorry_id]
    li = [i for i in invoices if i["lorry_id"]==lorry_id]
    fuel_total = sum(float(f["cost_gbp"]) for f in lf)
    vat_total  = sum(float(f["vat_gbp"]) for f in lf)
    paid_total = sum(float(i["amount_gbp"]) for i in li if i["status"]=="Paid")
    out_total  = sum(float(i["amount_gbp"]) for i in li if i["status"]=="Outstanding")
    alerts     = build_alerts(props, lorry_list, invoices)
    return render_template("lorry_detail.html", page="lorries",
        lorry=lorry, fuel=lf, invoices=li,
        fuel_total=fuel_total, vat_total=vat_total,
        paid_total=paid_total, out_total=out_total, alerts=alerts)

@app.route("/tasks", methods=["GET","POST"])
@login_required
def tasks():
    props    = load_props()
    task_list = load_tasks()
    alerts   = build_alerts(props, load_lorries(), load_invoices())
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            task_list.append({
                "task": request.form["task"],
                "done": False,
                "tag": request.form.get("tag",""),
                "priority": request.form.get("priority","medium"),
                "added_by": "James",
                "date_added": date.today().isoformat()
            })
            save_tasks(task_list)
        elif action == "toggle":
            idx = int(request.form["idx"])
            task_list[idx]["done"] = not bool(task_list[idx]["done"])
            save_tasks(task_list)
        elif action == "undo":
            idx = int(request.form["idx"])
            task_list[idx]["done"] = False
            save_tasks(task_list)
        return redirect(url_for("tasks"))
    pending   = [(i,t) for i,t in enumerate(task_list) if not t["done"]]
    completed = [(i,t) for i,t in enumerate(task_list) if t["done"]]
    return render_template("tasks.html", page="tasks",
        pending=pending, completed=completed,
        total=len(task_list), alerts=alerts,
        today=date.today().strftime("%A, %d %B %Y"))

@app.route("/alerts")
@login_required
def alerts_page():
    props    = load_props()
    lorries  = load_lorries()
    invoices = load_invoices()
    alerts   = build_alerts(props, lorries, invoices)
    high   = [a for a in alerts if a["level"]=="high"]
    med    = [a for a in alerts if a["level"]=="med"]
    low    = [a for a in alerts if a["level"]=="low"]
    return render_template("alerts.html", page="alerts",
        alerts=alerts, high=high, med=med, low=low)

@app.route("/maintenance", methods=["GET","POST"])
@login_required
def maintenance():
    props  = load_props()
    maint  = load_maint()
    alerts = build_alerts(props, load_lorries(), load_invoices())
    if request.method == "POST":
        maint.append({
            "property": request.form["property"],
            "date": date.today().isoformat(),
            "issue": request.form["issue"],
            "status": request.form["status"],
            "cost": request.form.get("cost", 0),
            "notes": request.form.get("notes",""),
            "logged_by": "James"
        })
        save_maint(maint)
        return redirect(url_for("maintenance"))
    ip   = [m for m in maint if m["status"]=="In Progress"]
    comp = [m for m in maint if m["status"]=="Completed"]
    comp.sort(key=lambda x: x["date"], reverse=True)
    total_cost = sum(float(m["cost"]) for m in maint)
    return render_template("maintenance.html", page="maintenance",
        props=props, ip=ip, comp=comp, total_cost=total_cost, alerts=alerts)

# ── API for charts ─────────────────────────────────────────────────────────────
@app.route("/api/cashflow")
@login_required
def api_cashflow():
    return jsonify(load_cashflow())

@app.route("/api/fuel_by_lorry")
@login_required
def api_fuel_by_lorry():
    fuel = load_fuel()
    by_lorry = {}
    for f in fuel:
        by_lorry[f["reg"]] = by_lorry.get(f["reg"],0) + float(f["cost_gbp"])
    return jsonify([{"reg":k,"cost":v} for k,v in by_lorry.items()])

@app.route("/containers", methods=["GET","POST"])
@login_required
def containers():
    props = load_props()
    alerts = build_alerts(props, load_lorries(), load_invoices())
    container_list = load_containers()
    rate = 100
    if request.method == "POST":
        # Check if container_id exists — update if so
        cid = request.form.get("container_id","")
        found = False
        for c in container_list:
            if c.get("container_id") == cid:
                c["size"]         = request.form.get("size","")
                c["type"]         = request.form.get("type","")
                c["status"]       = request.form.get("status","Vacant")
                c["monthly_rate"] = request.form.get("monthly_rate", rate)
                c["hirer_name"]   = request.form.get("hirer_name","")
                c["hirer_phone"]  = request.form.get("hirer_phone","")
                c["hire_start"]   = request.form.get("hire_start","")
                c["hire_end"]     = request.form.get("hire_end","")
                c["notes"]        = request.form.get("notes","")
                found = True
                break
        if not found:
            container_list.append({
                "container_id": cid,
                "size":         request.form.get("size","20ft"),
                "type":         request.form.get("type","Standard"),
                "status":       request.form.get("status","Vacant"),
                "monthly_rate": request.form.get("monthly_rate", rate),
                "hirer_name":   request.form.get("hirer_name",""),
                "hirer_phone":  request.form.get("hirer_phone",""),
                "hire_start":   request.form.get("hire_start",""),
                "hire_end":     request.form.get("hire_end",""),
                "notes":        request.form.get("notes",""),
            })
        save_containers(container_list)
        log_activity(
            f"Container {cid} updated — {request.form.get('status','Vacant')}",
            'Containers', 'containers', '📦'
        )
        return redirect(url_for("containers"))

    hired   = [c for c in container_list if str(c.get("status","")).lower() == "hired"]
    vacant  = [c for c in container_list if str(c.get("status","")).lower() != "hired"]
    hired_income  = sum(float(c.get("monthly_rate",rate) or rate) for c in hired)
    vacant_count  = len(vacant)
    hired_count   = len(hired)
    occupancy_pct = round(hired_count / len(container_list) * 100) if container_list else 0

    return render_template("containers.html", page="containers",
        containers=container_list, hired=hired, vacant=vacant,
        hired_count=hired_count, vacant_count=vacant_count,
        hired_income=hired_income, occupancy_pct=occupancy_pct,
        rate=rate, alerts=alerts)

@app.route("/performance")
@login_required
def performance():
    props = load_props()
    alerts = build_alerts(props, load_lorries(), load_invoices())

    ranked = []
    for p in props:
        rent = 0
        try: rent = float(p.get('monthly_rent', 0)) if str(p.get('monthly_rent','')).strip() not in ['','nan'] else 0
        except: rent = 0

        mtg = 0
        try: mtg = float(p.get('mortgage_monthly', 0)) if str(p.get('mortgage_monthly','')).strip() not in ['','nan'] else 0
        except: mtg = 0

        val = None
        try:
            v = p.get('mortgage_balance', '')
            # Use a rough estimate if no value — skip yield calc
            val = None
        except: val = None

        net = rent - mtg
        yield_pct = None

        ranked.append({
            'property': p['property'],
            'est_value': val,
            'rent': rent,
            'mortgage_monthly': mtg,
            'net_monthly': net,
            'yield_pct': yield_pct,
            'rent_status': p.get('rent_status',''),
        })

    ranked.sort(key=lambda x: x['net_monthly'], reverse=True)
    total_net = sum(r['net_monthly'] for r in ranked)
    negative_count = len([r for r in ranked if r['net_monthly'] < 0])
    best  = ranked[0]  if ranked else {'property':'—','net_monthly':0}
    worst = ranked[-1] if ranked else {'property':'—','net_monthly':0}

    import json as _json
    ranked_json = _json.dumps([{
        'property': r['property'],
        'net_monthly': float(r['net_monthly'] or 0),
        'yield_pct': float(r['yield_pct']) if r.get('yield_pct') else None,
        'rent_status': str(r.get('rent_status',''))
    } for r in ranked])
    return render_template('performance.html', page='performance',
        ranked=ranked, ranked_json=ranked_json, total_net=total_net, negative_count=negative_count,
        best=best, worst=worst, alerts=alerts)

@app.route("/map")
@login_required
def property_map():
    props = load_props()
    alerts = build_alerts(props, load_lorries(), load_invoices())
    occupied = [p for p in props if p["rent_status"] != "Vacant"]
    total_rent = sum(float(p["monthly_rent"]) for p in occupied if str(p.get("monthly_rent","")) not in ["","nan"])

    # Property coordinates — Suffolk locations
    coords = {
        "5 Queensway Mildenhall":         (52.3441, 0.5089),
        "5 Beeches Road West Row":         (52.3612, 0.5234),
        "22 Fleming Avenue Mildenhall":    (52.3428, 0.5071),
        "1 Bernards Close Mildenhall":     (52.3398, 0.5102),
        "3 Bernards Close Mildenhall":     (52.3399, 0.5103),
        "4 Bernards Close Mildenhall":     (52.3400, 0.5104),
        "1A Vinrose Lodge Mildenhall":     (52.3442, 0.5090),
        "5a Beeches Road West Row":        (52.3613, 0.5235),
        "5b Beeches Road West Row":        (52.3614, 0.5236),
        "Ponderosa West Row":              (52.3580, 0.5190),
        "Ponderosa Annex West Row":        (52.3581, 0.5191),
        "St Michaels Thetford":            (52.4142, 0.7432),
        "Garrod House Flat 1 Lakenheath":  (52.4089, 0.5321),
        "Garrod House Flat 2 Lakenheath":  (52.4090, 0.5322),
        "Garrod House Flat 3 Lakenheath":  (52.4091, 0.5323),
        "Garrod House Flat B Lakenheath":  (52.4092, 0.5324),
        "Sparks Farm Hurdle Drove":        (52.3901, 0.4980),
        "Cottage Lakenheath":              (52.4085, 0.5318),
        "Airview House West Row":          (52.3615, 0.5237),
        "Airview Annex West Row":          (52.3616, 0.5238),
        "The Shed West Row":               (52.3618, 0.5240),
    }

    map_data = []
    for p in props:
        lat, lng = coords.get(p["property"], (52.38, 0.54))
        map_data.append({
            "property":        p["property"],
            "address":         p["address"],
            "lat":             lat,
            "lng":             lng,
            "monthly_rent":    p.get("monthly_rent", 0),
            "mortgage_monthly":p.get("mortgage_monthly", 0),
            "mortgage_lender": p.get("mortgage_lender", ""),
            "rent_status":     p.get("rent_status", ""),
        })

    return render_template("map.html", page="map",
        props=props, map_data=map_data,
        total_rent=total_rent, alerts=alerts)

@app.route("/compliance", methods=["GET","POST"])
@login_required
def compliance():
    from datetime import date, datetime
    props = load_props()
    alerts = build_alerts(props, load_lorries(), load_invoices())
    docs = load_documents()
    today = date.today()

    if request.method == "POST":
        prop = request.form.get("property","")
        dtype = request.form.get("document_type","")
        for d in docs:
            if d.get("property") == prop and d.get("document_type") == dtype:
                d["expiry_date"] = request.form.get("expiry_date","")
                d["drive_link"]  = request.form.get("drive_link","")
                d["notes"]       = request.form.get("notes","")
                break
        else:
            docs.append({
                "property":      prop,
                "document_type": dtype,
                "expiry_date":   request.form.get("expiry_date",""),
                "drive_link":    request.form.get("drive_link",""),
                "notes":         request.form.get("notes",""),
            })
        save_documents(docs)
        return redirect(url_for("compliance"))

    # Categorise docs
    expired_docs  = []
    expiring_docs = []
    pending_docs  = []
    for d in docs:
        exp = d.get("expiry_date")
        if not exp or str(exp) in ["","None","nan"]:
            pending_docs.append(d)
        else:
            try:
                exp_date = datetime.strptime(str(exp)[:10], "%Y-%m-%d").date()
                days_left = (exp_date - today).days
                d["days_left"] = days_left
                if days_left < 0:
                    expired_docs.append(d)
                elif days_left <= 90:
                    expiring_docs.append(d)
            except:
                pending_docs.append(d)

    # Tenancy renewals — next 6 months
    renewals = []
    for p in props:
        end = p.get("tenancy_end","")
        if end and str(end) not in ["","SPT","nan","None","—"]:
            try:
                end_date = datetime.strptime(str(end)[:10], "%Y-%m-%d").date()
                days_left = (end_date - today).days
                if 0 <= days_left <= 180:
                    renewals.append({
                        "property": p["property"],
                        "end_date": str(end)[:10],
                        "days_left": days_left,
                        "rent": float(p.get("monthly_rent",0) or 0),
                        "lender": p.get("mortgage_lender",""),
                    })
            except: pass
    renewals.sort(key=lambda x: x["days_left"])

    return render_template("compliance.html", page="compliance",
        expired_docs=expired_docs, expiring_docs=expiring_docs, pending_docs=pending_docs,
        expired_count=len(expired_docs), expiring_count=len(expiring_docs),
        pending_count=len(pending_docs), renewals=renewals, renewals_count=len(renewals),
        all_props=props, alerts=alerts)

@app.route("/problem-occupants", methods=["GET","POST"])
@login_required
def problem_occupants():
    props = load_props()
    alerts = build_alerts(props, load_lorries(), load_invoices())
    occ_list = load_problem_occupants()
    if request.method == "POST":
        from datetime import date
        today = date.today()
        date_rep = request.form.get("date_reported","")
        days = None
        if date_rep:
            try:
                reported = date.fromisoformat(date_rep)
                days = (today - reported).days
            except: pass
        loss = float(request.form.get("estimated_loss_per_month",0) or 0)
        occ_list.append({
            "property":    request.form.get("property",""),
            "occupant_name": request.form.get("occupant_name",""),
            "issue_type":  request.form.get("issue_type",""),
            "date_reported": date_rep,
            "days_since":  days,
            "legal_stage": request.form.get("legal_stage",""),
            "solicitor":   request.form.get("solicitor",""),
            "next_action": request.form.get("next_action",""),
            "next_action_date": request.form.get("next_action_date",""),
            "estimated_loss_per_month": loss,
            "notes":       request.form.get("notes",""),
        })
        save_problem_occupants(occ_list)
        return redirect(url_for("problem_occupants"))
    total_loss = sum(float(o["estimated_loss_per_month"]) for o in occ_list if o.get("estimated_loss_per_month"))
    total_lost_to_date = sum(
        float(o["estimated_loss_per_month"]) * (o["days_since"] or 0) / 30
        for o in occ_list if o.get("estimated_loss_per_month") and o.get("days_since")
    )
    legal_count = len([o for o in occ_list if o.get("legal_stage") and o["legal_stage"] not in ["","None","None instructed",None]])
    return render_template("problem_occupants.html", page="problem_occupants",
        occupants=occ_list, total_loss=total_loss,
        total_lost_to_date=total_lost_to_date,
        legal_count=legal_count, all_props=props, alerts=alerts)

@app.route("/deposits", methods=["GET","POST"])
@login_required
def deposits():
    props = load_props()
    alerts = build_alerts(props, load_lorries(), load_invoices())
    dep_list = load_deposits()
    if request.method == "POST":
        prop = request.form.get("property","")
        for d in dep_list:
            if d["property"] == prop:
                d["tenant_name"]    = request.form.get("tenant_name","")
                d["deposit_amount"] = request.form.get("deposit_amount","")
                d["scheme"]         = request.form.get("scheme","")
                d["certificate_ref"]= request.form.get("certificate_ref","")
                d["date_protected"] = request.form.get("date_protected","")
                d["scheme_url"]     = request.form.get("scheme_url","")
                break
        save_deposits(dep_list)
        return redirect(url_for("deposits"))
    total_deposits  = sum(float(d["deposit_amount"]) for d in dep_list if d.get("deposit_amount") and str(d["deposit_amount"]) not in ["","None","nan"])
    protected_count = len([d for d in dep_list if d.get("scheme") and str(d["scheme"]) not in ["","None","nan"]])
    unprotected_count = len([d for d in dep_list if d.get("deposit_amount") and str(d["deposit_amount"]) not in ["","None","nan"] and (not d.get("scheme") or str(d["scheme"]) in ["","None","nan"])])
    empty_count     = len([d for d in dep_list if not d.get("deposit_amount") or str(d["deposit_amount"]) in ["","None","nan"]])
    return render_template("deposits.html", page="deposits",
        deposits=dep_list, total_deposits=total_deposits,
        protected_count=protected_count, unprotected_count=unprotected_count,
        empty_count=empty_count, alerts=alerts)

@app.route("/vat-invoices", methods=["GET","POST"])
@login_required
def vat_invoices():
    props = load_props()
    alerts = build_alerts(props, load_lorries(), load_invoices())
    inv_list = load_vat_invoices()
    if request.method == "POST":
        amt = float(request.form.get("amount_gbp",0) or 0)
        vat = float(request.form.get("vat_gbp",0) or 0)
        inv_list.append({
            "invoice_id":  request.form.get("invoice_id",""),
            "date":        request.form.get("date",""),
            "category":    request.form.get("category",""),
            "supplier":    request.form.get("supplier",""),
            "description": request.form.get("description",""),
            "amount_gbp":  amt,
            "vat_gbp":     vat,
            "total_gbp":   amt + vat,
            "status":      request.form.get("status","Outstanding"),
            "drive_link":  request.form.get("drive_link",""),
            "notes":       request.form.get("notes",""),
        })
        save_vat_invoices(inv_list)
        log_activity(
            f"{request.form.get('supplier','')} invoice added — £{float(request.form.get('total_gbp',0) or 0):.2f}",
            request.form.get('category','Invoice'),
            'vat_invoices', '📄'
        )
        return redirect(url_for("vat_invoices"))
    outstanding_total = sum(float(i["total_gbp"]) for i in inv_list if i.get("status")=="Outstanding" and i.get("total_gbp"))
    outstanding_count = len([i for i in inv_list if i.get("status")=="Outstanding"])
    vat_total = sum(float(i["vat_gbp"]) for i in inv_list if i.get("vat_gbp"))
    return render_template("vat_invoices.html", page="vat_invoices",
        invoices=inv_list, outstanding_total=outstanding_total,
        outstanding_count=outstanding_count, vat_total=vat_total, alerts=alerts)

@app.context_processor
def inject_now():
    return {"now": datetime.now().strftime("%H:%M")}

if __name__ == "__main__":
    app.run(debug=True, port=5000)
