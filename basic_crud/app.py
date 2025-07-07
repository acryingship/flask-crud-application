import time
import pymysql
import requests
import secrets
from flask import Flask, render_template, request, redirect, json, session, url_for, flash
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import uuid
from sqlalchemy import text

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
Scss(app)
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:root123@172.16.10.200:3306/evo_wes_inventory"
db = SQLAlchemy(app)
#app.run(host="0.0.0.0", port=5000)

class Inventory(db.Model):
    """A Model for an Item in the Todo List

    Args:
        db (_type_): database model

    Returns:
        __repr__: string rep.
    """
    __tablename__ = 'level2_inventory'
    id = db.Column(db.Integer, primary_key=True)
    zone_code = db.Column(db.String)
    #sku_code = db.Column(db.String)
    out_locked_quantity = db.Column(db.Integer)
    in_locked_quantity = db.Column(db.Integer)
    quantity = db.Column(db.Integer)
    
    def __repr__(self):
        return f"<Inventory {self.zone_code}, {self.sku_code}, {self.quantity - self.out_locked_quantity}>"

@app.route('/', methods=["POST","GET"])

def index():
    # Get first 50 rows as an example
    sku_name_dict = {'CeMAT_LEGO': 'LEGO-L', 'CeMAT_LEGO_S': 'LEGO-S', 'CeMAT_Pen': 'PEN', 'CeMAT_Tote': 'TOTE BAG',
                     'CeMAT_Charger': 'WIRELESS CHARGER', 'CeMAT_USB': 'USB'}
    sql = text("""SELECT zone_code,sku_code, out_locked_quantity,in_locked_quantity, quantity FROM evo_wes_inventory.level2_inventory l2 LEFT JOIN evo_wes_basic.basic_sku bs ON l2.sku_id = bs.id WHERE sku_code LIKE 'CeMAT%';""")
    result = db.session.execute(sql)
    rows = result.fetchall()
    print(rows)
    sku_list = []
    filtered_rows =[row for row in rows if row.quantity>0 and row.zone_code=='AMR']
    print(filtered_rows)
    newRows = []
    for row in filtered_rows:
        zone = row[0]
        sku = row[1]
        outlocked = row[2]
        quantity = row[4]
        renamedSku = sku_name_dict[sku]
        sku_list.append(renamedSku)
        newRow = (zone,renamedSku,outlocked,0,quantity)
        newRows.append(newRow)
    sku_list = set(sku_list)
    print(newRows)
    print(sku_list)

    return render_template("index.html", rows=newRows, skulist = list(sku_list))


@app.route('/submit', methods=['POST'])
def submit():
    sku_name_dict = {'CeMAT_LEGO': 'LEGO-L', 'CeMAT_LEGO_S': 'LEGO-S', 'CeMAT_Pen': 'PEN', 'CeMAT_Tote': 'TOTE BAG',
                     'CeMAT_Charger': 'WIRELESS CHARGER', 'CeMAT_USB': 'USB'}
    invDict = {key:value for value,key in sku_name_dict.items()}
    sku_data =  request.form.getlist('sku')
    print(sku_data)
    selected_skus =[invDict[sku] for sku in sku_data]
    print(selected_skus)
    selected_quantity = int(request.form.get('quantity'))
    bill_date = datetime.now()
    bill_date = bill_date.strftime("%d-%m-%Y %H:%M:%S")
    # Example: just print it or use it in logic
    print(f"{bill_date} \nSKU: {','.join(selected_skus)}, Quantity: {selected_quantity}")
    results_str = f"{bill_date} \nSKU: {selected_skus}, Quantity: {selected_quantity}"
    #pickResults = makePick(selected_sku,selected_quantity)
    if not selected_skus or not selected_quantity:
        flash("Please select SKU and quantity")
    for i in range(selected_quantity):
        print(i)
        pickResults = makePickMultiLine(selected_skus,selected_quantity)
        results_str += "\n" + pickResults
        time.sleep(1)
        flash(results_str)

    return redirect(url_for('index'))

def makePickMultiLine(sku_entry,qt_entry):
    url = 'http://172.16.10.200:10080/api/v2/quicktron/wes/picking-order/create'

    # Get user input for the number of requests, SKU codes and their quantities
    bill_type = 'SMALL'
    sku_code = sku_entry
    sku_quant = int(qt_entry)

    # bill_type = "MEDIUM"
    bill_header = "fOUT-" + bill_type  # user-defined bill header""
    # Check if the number of SKUs and quantities match

    # Define the headers
    headers = {
        "appKey": "0123456789abcdef",
        "appSecret": "0123456789abcdef",
        "requestId": str(int(time.time())),
        "timestamp": str(int(time.time())),
        "version": "2.7",
        "Content-Type": "application/json"
    }
    start_time = time.time()
    # Send the POST request for a user defined number of times

    bill_date = datetime.now()
    ship_deadline = bill_date + timedelta(hours=5)
    order_id = uuid.uuid4().int

    # Create a dictionary for each SKU in the "details" list
    details = []
    detail_id = 0

    for sku_code in sku_entry:
        detail_id += 1
        sku_code = sku_code.strip()  # Remove any leading/trailing whitespace
        details.append({
            "id": str(order_id + detail_id),
            "ownerCode": "1",
            "skuCode": sku_code,  # user-defined SKU code
            "quantity": 1,  # user-defined quantity
            "lotAtt01": None,
            "lotAtt02": None,
            "lotAtt03": None
        })

    payload = {
        "transactional": True,
        "warehouseCode": "TTC_demo",
        "data": [
            {
                "id": str(order_id),  # unique id
                "billNumber": bill_header + bill_date.strftime("%d-%m-%Y %H:%M:%S"),  # unique billNumber
                "ownerCode": "1",  # constant ownerCode
                "billType": bill_type,  # user-defined billType
                "billDate": bill_date.strftime("%d-%m-%Y %H:%M:%S"),  # unique billDate
                "priorityType": "COMMON",
                "priorityValue": 1,
                "shipDeadline": ship_deadline.strftime("%d-%m-%Y %H:%M:%S"),  # billDate + 5 hours
                # "udf1": "",
                "remark": "",
                "details": details
            }
        ]
    }

    # Convert dict to json string
    data = json.dumps(payload)
    print(data)
    response = requests.post(url, headers=headers, data=data)
    end_time = time.time()
    elapsed_time = end_time - start_time

    print(
        f"Application sent 1 requests, in {elapsed_time} seconds\n Average time per request: {elapsed_time / 1} seconds.")
    # Print the response
    print(response.text)
    time.sleep(1)
    return response.text


def makePick(sku_entry,qt_entry):
    # Define the URL
    url = 'http://172.16.10.200:10080/api/v2/quicktron/wes/picking-order/create'

    # Get user input for the number of requests, SKU codes and their quantities
    bill_type = 'SMALL'
    sku_code = sku_entry
    sku_quant = int(qt_entry)

    #bill_type = "MEDIUM"
    bill_header = "fOUT-" + bill_type  # user-defined bill header""
    # Check if the number of SKUs and quantities match

    # Define the headers
    headers = {
        "appKey": "0123456789abcdef",
        "appSecret": "0123456789abcdef",
        "requestId": str(int(time.time())),
        "timestamp": str(int(time.time())),
        "version": "2.7",
        "Content-Type": "application/json"
    }
    start_time = time.time()
    # Send the POST request for a user defined number of times


    bill_date = datetime.now()
    ship_deadline = bill_date + timedelta(hours=5)
    order_id = uuid.uuid4().int

    # Create a dictionary for each SKU in the "details" list
    details = []
    detail_id=0

    sku_code = sku_code.strip()  # Remove any leading/trailing whitespace
    details.append({
        "id": str(order_id+detail_id),
        "ownerCode": "1",
        "skuCode": sku_code,  # user-defined SKU code
        "quantity": sku_quant,  # user-defined quantity
        "lotAtt01": None,
        "lotAtt02": None,
        "lotAtt03": None
    })

    payload = {
        "transactional": True,
        "warehouseCode": "TTC_demo",
        "data": [
            {
                "id": str(order_id),  # unique id
                "billNumber": bill_header + bill_date.strftime("%d-%m-%Y %H:%M:%S"),  # unique billNumber
                "ownerCode": "1",  # constant ownerCode
                "billType": bill_type,  # user-defined billType
                "billDate": bill_date.strftime("%d-%m-%Y %H:%M:%S"),  # unique billDate
                "priorityType": "COMMON",
                "priorityValue": 1,
                "shipDeadline": ship_deadline.strftime("%d-%m-%Y %H:%M:%S"),  # billDate + 5 hours
                #"udf1": "",
                "remark": "",
                "details": details
            }
        ]
    }

    # Convert dict to json string
    data = json.dumps(payload)
    print(data)
    response = requests.post(url, headers=headers, data=data)
    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"Application sent 1 requests, in {elapsed_time} seconds\n Average time per request: {elapsed_time/1} seconds.")
        # Print the response
    print(response.text)
    time.sleep(1)
    return response.text

if __name__ in "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)