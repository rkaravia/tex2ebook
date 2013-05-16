# run with --help to see available options

import os, sys, tempfile, shutil, re
from optparse import OptionParser

log_dir = os.path.abspath('_log')

def get_working_dir(texfile, log):
	if log:
		# create a subdirectory in _log
		if not os.path.exists(log_dir):
			os.makedirs(log_dir)
		subdir = os.path.join(log_dir, '%s-files' % os.path.splitext(os.path.basename(texfile))[0])
		working_dir = os.path.join(log_dir, subdir)
		if os.path.exists(working_dir):
			shutil.rmtree(working_dir)
		os.mkdir(working_dir)
		return working_dir
	else:
		# create a temporary directory in system tmp
		return tempfile.mkdtemp()
	
# convert all files listed in indexfile
def batch(indexfile, log, ebook_ext):
	print "--- Using batch file %s" % indexfile
	indexroot = os.path.abspath(os.path.dirname(indexfile))
	for texfilerel in open(indexfile):
		texfile = os.path.join(indexroot, texfilerel.strip())
		convert(texfile, log, ebook_ext)

# convert a single file
def convert(texfile, log, ebook_ext, dest=None):
	print "--- Converting file %s" % texfile
	basename = os.path.basename(texfile)
	title = os.path.splitext(basename)[0]
	working_dir = get_working_dir(texfile, log)
	
	print "--- Working dir is %s" % working_dir
	os.chdir(os.path.join('./', os.path.dirname(texfile)))
	
	html = os.path.join(working_dir, '%s.html' % title)
	log_hevea = os.path.join(working_dir, 'hevea.log')
	hevea = 'hevea %s -o %s >> %s' % (basename, html, log_hevea)
	print "--- Invoking hevea..."
	print hevea
	os.system(hevea)
	os.system('bibhva %s >> %s' % (os.path.join(working_dir, title), log_hevea))
	os.system(hevea)
	os.system(hevea)

	imagen = 'imagen -pdf %s >> %s' % (os.path.join(working_dir, title), log_hevea)
	print "--- Invoking imagen..."
	print imagen
	os.system(imagen)
	
	if dest == None:
		dest = '%s.%s' % (title, ebook_ext)
	# add extension specific options
	ext_options = ''
	if ebook_ext == 'epub':
		ext_options = '--no-default-epub-cover'
	log_ebook = os.path.join(working_dir, 'ebook-convert.log')
	ebookconvert = 'ebook-convert %s %s %s --page-breaks-before / --toc-threshold 0 --level1-toc //h:h2 --level2-toc //h:h3 --level3-toc //h:h4 >> %s' % (html, dest, ext_options, log_ebook)
	print "--- Invoking ebook-convert..."
	print ebookconvert
	os.system(ebookconvert)
	print "--- Result written to %s" % dest
	
# convert equations to images
# added 25.04.2013 ML
# infos de http://webcache.googleusercontent.com/search?q=cache:V3iGRJDdHDIJ:comments.gmane.org/gmane.comp.tex.hevea/192+&cd=3&hl=en&ct=clnk&client=firefox-a
# fonction pompée de http://stackoverflow.com/questions/39086/search-and-replace-a-line-in-a-file-in-python$
# http://en.wikibooks.org/wiki/LaTeX/Mathematics
def equ_to_images(texfile):
	print "--- Converting equations to images for file %s" % texfile
	(head, tail) = os.path.split(texfile)
	(root, ext) = os.path.splitext(tail)
	new_root = '%s_eq_to_images' % root
	new_texfile = os.path.join(head, new_root + ext)
	new_file = open(new_texfile, 'w')
	old_file = open(texfile)
	# define new environment
	new_file.write('\\newenvironment{equ_to_image}{\\begin{toimage}\\(}{\\)\\end{toimage}\\imageflush}')
	for line in old_file:
		new_line = line
		# replace all possible equation start and end tags by new environment tags (only $ and $$ are not replaced)
		new_line = new_line.replace('\\(', '\\begin{equ_to_image}')
		new_line = new_line.replace('\\begin{math}', '\\begin{equ_to_image}')
		new_line = new_line.replace('\\[', '\\begin{equ_to_image}')
		new_line = new_line.replace('\\begin{displaymath}', '\\begin{equ_to_image}')
		new_line = new_line.replace('\\begin{equation}', '\\begin{equ_to_image}')
		new_line = new_line.replace('\\)', '\\end{equ_to_image}')
		new_line = new_line.replace('\\end{math}', '\\end{equ_to_image}')
		new_line = new_line.replace('\\]', '\\end{equ_to_image}')
		new_line = new_line.replace('\\end{displaymath}', '\\end{equ_to_image}')
		new_line = new_line.replace('\\end{equation}', '\\end{equ_to_image}')
		new_file.write(new_line)
	#close temp file
	new_file.close()
	old_file.close()
	return new_texfile

usage = "usage: %prog [options] file"
parser = OptionParser(usage=usage)
parser.add_option("-l", "--log", action="store_true", dest="log", default=False, help="keep the intermediate files")
parser.add_option("-b", "--batch", action="store_true", dest="batch", default=False, help="process several files in batch mode")
parser.add_option("-k", "--kindle", action="store_true", dest="kindle", default=False, help="convert to MOBI rather than EPUB (default)")
parser.add_option("-i", "--equ_to_images", action="store_true", dest="images", default=False, help="convert equations to images")
parser.add_option("-o", "--output", dest="outfile", help="output filename")

(options, params) = parser.parse_args()

if options.kindle:
	ext = 'mobi'
else:
	ext = 'epub'

if len(params) == 0:
	print "No file specified!"
else:
	if options.batch:
		batch(params[-1], options.log, ext)
	else:
		texfile = params[-1]
		if options.images:
			texfile = equ_to_images(texfile)
		if options.outfile == None:
			convert(texfile, options.log, ext)
		else:
			convert(texfile, options.log, ext, os.path.abspath(options.outfile))