import os, subprocess, time, uuid

# flask
from flask import Flask, jsonify, render_template, request, Response, url_for
from werkzeug import secure_filename

# threading
from threading import Thread
from Queue import Queue, Empty

# jinja templating
from jinja2 import Environment
from jinja2.loaders import FileSystemLoader

# configuration
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'upload'
app.config['DOWNLOAD_FOLDER'] = 'static/download'
app.config['TIMEOUT'] = 60

# Separate thread which performs blocking reads on stdout and adds new lines to queue
def enqueue_output(out, queue):
	for line in iter(out.readline, b''):
		queue.put(line)
	print 'Output listener stopped.'
	out.close()

# Create subdirectory of root
def dir_uuid(root, fileid):
	dir = os.path.join(root, fileid)
	os.mkdir(dir)
	return dir

# find first .tex file in subdirs of dir
def find_tex(dir):
	for dirpath, dirnames, filenames in os.walk(dir):
		for filename in filenames:
			if filename.endswith(".tex"):
				return os.path.join(dirpath, filename)
	return ''

def println(msg = ''):
	return msg + '<br />'

@app.route('/convert', methods=['POST'])
def convert():
	# save uploaded file in subdir with random identifier
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
			yield println('Extracting contents of archive...')
			os.system('unzip %s -d %s' % (fPath, fDir))
			texFile = find_tex(fDir)
		elif fExt == '.tex':
			texFile = fPath
		else:
			yield println('File format not recognized: %s' % fExt)

		if texFile == '':
			yield println('No input file found.')
		else:
			epubFile = '%s.epub' % fRoot
			epubPath = os.path.join(dir_uuid(app.config['DOWNLOAD_FOLDER'], fileid), epubFile)
			yield println('Received file %s, converting to %s' % (os.path.basename(texFile), epubFile))
			# Launch conversion script
			proc = subprocess.Popen(
				['python', '-u', 'tex2ebook.py', '-o', epubPath, texFile],
				stdout=subprocess.PIPE,
				stderr=open(os.devnull, 'w')
			)
			# Start separate thread to read stdout
			q = Queue()
			t = Thread(target=enqueue_output, args=(proc.stdout, q))
			t.deamon = True
			t.start()
			start = time.time()
			running = True
			# Read stdout from other thread every second, stop if timeout
			while running and time.time() - start < app.config['TIMEOUT']:
				running = proc.poll() is None
				try:
					line = q.get(timeout=1)
				except Empty:
					line = ''
				else:
					yield println(line.rstrip())

			if running:
				yield println('Timed out.')
				# Kill subprocess if timeout occurred
				proc.kill()
			else:
				yield println()
				yield println('Done.')
				# Redirect to result file
				yield '<script type="text/javascript"> $(document).ready(function() { window.location.href = "%s"; }); </script>' % epubPath
				yield 'If the download does not start automatically, please click <a href="%s">here</a>.' % epubPath

	# Stream the response using the result.html template
	env = Environment(loader=FileSystemLoader('templates'))
	tmpl = env.get_template('result.html')
	return Response(tmpl.generate(result=streamResponse()))

@app.route('/')
def index():
	return render_template('index.html')

if __name__ == '__main__':
	app.run(host='0.0.0.0')
	# app.run(debug=True)
