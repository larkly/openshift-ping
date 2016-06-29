from flask import Flask
from flask import render_template
from flask import redirect
import subprocess

app = Flask(__name__)

def filter_output(output, host):
    o_filter = ""
    for line in output.stdout:
        o_filter = o_filter+line

    return_data = "%s" % host + " " +  o_filter
    return return_data

@app.route('/')
def index():
    return redirect("/ping", code=302)

@app.route('/ping')
@app.route('/ping/<host>')
def ping(host=None):
    if host is None:
        return render_template('results.html', return_data='You need to enter an IP address at the end of the URL, like <domain>/ping/8.8.8.8')
    else:
        cmd = "ping -c 4 %s" % host
        output = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        return_data = filter_output(output, host)
        return render_template('results.html', return_data=return_data)

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0',port=8080)
