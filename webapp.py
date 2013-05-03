import os
import subprocess
import time
import uuid
from flask import Flask, jsonify, render_template, request, Response, url_for
from werkzeug import secure_filename

from threading import Thread
from Queue import Queue, Empty

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'upload'
app.config['DOWNLOAD_FOLDER'] = 'static/download'
app.config['TIMEOUT'] = 60

def enqueue_output(out, queue):
	for line in iter(out.readline, b''):
		queue.put(line)
	print 'Output listener stopped.'
	out.close()

def dir_uuid(root, fileid):
	dir = os.path.join(root, fileid)
	os.mkdir(dir)
	return dir

def find_tex(dir):
	for dirpath, dirnames, filenames in os.walk(dir):
		for filename in filenames:
			if filename.endswith(".tex"):
				return os.path.join(dirpath, filename)
	return ''

@app.route('/convert', methods=['POST'])
def convert():
	fileid = str(uuid.uuid4())
	file = request.files['file']
	f = secure_filename(file.filename)
	fDir = dir_uuid(app.config['UPLOAD_FOLDER'], fileid)
	fPath = os.path.join(fDir, f)
	file.save(fPath)

	def streamResponse():
		texFile = ''
		(fRoot, fExt) = os.path.splitext(f)
		if fExt == '.zip':
			yield 'Extracting contents of archive...'
			os.system('unzip %s -d %s' % (fPath, fDir))
			texFile = find_tex(fDir)
		elif fExt == '.tex':
			texFile = fPath
		else:
			yield 'File format not recognized: %s<br />\n' % fExt

		if texFile == '':
			yield 'No input file found.'
		else:
			epubFile = '%s.epub' % fRoot
			epubPath = os.path.join(dir_uuid(app.config['DOWNLOAD_FOLDER'], fileid), epubFile)
			yield 'Received file %s, converting to %s<br />\n' % (f, epubFile)
			proc = subprocess.Popen(
				['python', '-u', 'tex2ebook.py', '-o', epubPath, texFile],
				stdout=subprocess.PIPE,
				stderr=open(os.devnull, 'w')
			)
			q = Queue()
			t = Thread(target=enqueue_output, args=(proc.stdout, q))
			t.deamon = True
			t.start()
			start = time.time()
			running = True
			while running and time.time() - start < app.config['TIMEOUT']:
				running = proc.poll() is None
				try:
					line = q.get(timeout=.5)
				except Empty:
					line = ''
				else:
					yield line.rstrip() + '<br />\n'

			if running:
				yield 'Timed out.'
				proc.kill()
			else:
				yield '<a href="%s">Download</a>' % epubPath

	return Response(streamResponse())


@app.route('/')
def index():
	return render_template('index.html')


if __name__ == '__main__':
	app.run(debug=True)
