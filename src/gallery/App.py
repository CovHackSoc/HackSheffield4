import os
import sqlite3
from flask import Flask, render_template, send_from_directory, request, g


__author__='andytexi'

app = Flask(__name__)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATABASE = './db.sqlite3'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False, write=False):
    db = get_db()
    cur = db.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    if write == True:
        db.commit()
    return (rv[0] if rv else None) if one else rv

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


@app.route("/upload", methods=['GET', 'POST'])
def upload():
    if request.method == "GET":
        return render_template("upload.html")


    target = os.path.join(APP_ROOT,'images/')
    print(target)

    if not os.path.isdir(target):
        os.mkdir(target)
    else:
        print("couldn't create uploaded directory:{}".format(target))
    print(request.files.getlist("file"))

    episode = "unknown episode"
    if 'episode' in request.form:
        episode = request.form['episode']

    for upload in request.files.getlist("file"):
        print(upload)
        print("{}is the file name". format(upload.filename))
        filename = upload.filename
        destination = "/".join([target,filename])
        print("accept incoming file:", filename)
        print("save it to:", destination)
        upload.save(destination)

    query_db(
        'INSERT INTO uploads VALUES (?, ?, datetime(\'now\'));',
        [filename, episode],
        write=True
    )
    #hoq to download the picture
    #return send_from_directory("images",filename,as_attachment=True)
    return render_template("complete.html", image_name=filename)

@app.route('/upload/<filename>')
def send_image(filename):
    return send_from_directory("images", filename)


@app.route('/')
def get_gallery():
    #return a list with files
    image_names = os.listdir('./images')[::-1]
    #print(image_names)
    response = query_db('SELECT * FROM uploads ORDER BY datetime(date) DESC')
    return render_template("gallery.html", images=response)


#@app.route('/')
#@app.route('/index')
#def show_index():
#    full_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'bob.jpg')
#    return render_template("gallery.html", user_image = full_filename)

if __name__=="__main__":
    app.run(port=4555,debug=True)
