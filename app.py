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
    alerts        = build_alerts(props, lorries, invoices)

    return render_template("overview.html",
        page="overview",
        props=props, accounts=accounts, cashflow=cashflow,
        occupied=occupied, total_rent=total_rent, total_mtg=total_mtg,
        net_cf=net_cf, total_bal=total_bal, total_fuel=total_fuel,
        total_vat=total_vat, out_total=out_total,
        pending_tasks=pending_tasks[:5], alerts=alerts,
        today=datetime.now().strftime("%A, %d %B %Y"),
        urgent_alerts=[a for a in alerts if a["level"]=="high"],
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
    container_list = load_containers()
    alerts = build_alerts(props, load_lorries(), load_invoices())
    if request.method == "POST":
        container_list.append({
            "container_id": request.form.get("container_id",""),
            "location":     request.form.get("location",""),
            "size":         request.form.get("size",""),
            "type":         request.form.get("type",""),
            "status":       request.form.get("status","Vacant"),
            "monthly_income": request.form.get("monthly_income",0),
            "tenant":       request.form.get("tenant",""),
            "notes":        request.form.get("notes",""),
        })
        save_containers(container_list)
        return redirect(url_for("containers"))
    total_income = sum(float(c["monthly_income"]) for c in container_list if c.get("monthly_income"))
    return render_template("containers.html", page="containers",
        containers=container_list, total_income=total_income, alerts=alerts)

@app.context_processor
def inject_now():
    return {"now": datetime.now().strftime("%H:%M")}

if __name__ == "__main__":
    app.run(debug=True, port=5000)
