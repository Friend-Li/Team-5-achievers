from flask import Flask, render_template_string
from app_all_in_one import main
import pandas as pd

app = Flask(__name__)

logs = ""
table = ""
status = ""

HTML = """
<h1>CPR System</h1>

<form action="/run">
<button>Run System</button>
</form>

<h3>Status: {{status}}</h3>

<h3>Logs:</h3>
<div style="background:black;color:lime">{{logs|safe}}</div>

<h3>Students:</h3>
{{table|safe}}
"""

@app.route("/")
def home():
    return render_template_string(HTML, logs=logs, table=table, status=status)

@app.route("/run")
def run():
    global logs, table, status

    students, log_data = main()

    logs = "<br>".join(log_data)

    if students:
        table = pd.DataFrame(students).to_html(index=False)
        status = "Success"
    else:
        status = "No Data"

    return home()

if __name__ == "__main__":
    app.run(debug=True)