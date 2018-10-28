import os
from flask import Flask, render_template, send_from_directory, request


__author__='andytexi'

app = Flask(__name__)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))


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

    for upload in request.files.getlist("file"):
        print(upload)
        print("{}is the file name". format(upload.filename))
        filename= upload.filename
        destination = "/".join([target,filename])
        print("accept incoming file:", filename)
        print("save it to:", destination)
        upload.save(destination)

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
    print(image_names)
    return render_template("gallery.html", image_names=image_names)


#@app.route('/')
#@app.route('/index')
#def show_index():
#    full_filename = os.path.join(app.config['UPLOAD_FOLDER'], 'bob.jpg')
#    return render_template("gallery.html", user_image = full_filename)

if __name__=="__main__":
    app.run(port=4555,debug=True)
