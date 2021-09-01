import os
from flask import Flask, escape, request, render_template, url_for, flash, redirect, send_from_directory
from flask_uploads import UploadSet, configure_uploads
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
# from werkzeug.utils import secure_filename
from wtforms import SubmitField, StringField, validators
from flask_bootstrap import Bootstrap

import pandas as pd
import numpy as np
import datetime

'''
set FLASK_APP=hello.py
set FLASK_DEBUG=1
python -m flask run

If you get:
ImportError: cannot import name 'secure_filename'
You can use Flask-Reuploaded as a drop-in replacement to Flask-Uploads, which fixes your problem.
'''

basedir = os.path.abspath(os.path.dirname(__file__))
upload_dest = os.path.join(basedir, 'uploads')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bacon'
app.config['UPLOADED_CSVS_DEST'] = upload_dest # you'll need to create a folder named uploads
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 # sets maximum file size to 5MB
Bootstrap(app)

csv_set = UploadSet('csvs')
configure_uploads(app, csv_set)

class UploadForm(FlaskForm):
	users_csv = FileField('Users', validators=[FileRequired('File was empty!'), FileAllowed(['csv'], 'CSV only!')])
	maps_csv = FileField('MyE911 Device Mappings', validators=[FileRequired('File was empty!'), FileAllowed(['csv'], 'CSV only!')])
	devices_csv = FileField('Devices', validators=[FileRequired('File was empty!'), FileAllowed(['csv'], 'CSV only!')])
	pbx_name = StringField('PBX Name', [validators.required()])
	submit = SubmitField('Upload')

@app.route('/', methods=['GET', 'POST'])
def home():
	# if request.method == 'POST':
	# 	return 'You POSTed!'
	form = UploadForm()
	if form.validate_on_submit():
		filename1 = csv_set.save(form.users_csv.data)
		filename2 = csv_set.save(form.maps_csv.data)
		filename3 = csv_set.save(form.devices_csv.data)
		csv_urls = [filename1, filename2, filename3, form.pbx_name.data]
		# csv_urls = [csv_set.url(filename1), csv_set.url(filename2), csv_set.url(filename3)]

		report_results = generate_report(csv_urls)
		# flash('Files uploaded successfully.')
		# return redirect(url_for('home'))
	else:
		csv_urls = None
		report_results = None
	return render_template('home.html', form=form, file_url=csv_urls, results=report_results)

@app.route('/uploads/<name>')
def download_file(name):
    return send_from_directory(app.config['UPLOADED_CSVS_DEST'], name)

def generate_report(csv_urls):
	fname_users   = os.path.join(upload_dest, csv_urls[0])
	fname_maps    = os.path.join(upload_dest, csv_urls[1])
	fname_devices = os.path.join(upload_dest, csv_urls[2])
	pbx_name      = csv_urls[3]
	fname_output_fol  = "uploads\\"
	fname_output      = "mye911-checkup-"+datetime.datetime.now().strftime("%Y.%m.%d-%I.%M.%S")+".xlsx"
	fname_bulk_output = "missing-mye911-device_mappings-"+datetime.datetime.now().strftime("%Y.%m.%d-%I.%M.%S")+".csv"
	NoneType = type(None)

	#* 1 Load users csv file
	df_users = pd.read_csv(fname_users)
	print(f"File loaded successfully: {fname_users}")
	# Rename username column
	df_users.rename({'## Username': 'Username'}, axis='columns', inplace=True)
	# Delete unnecessary columns
	del df_users["Starting Building ID"]
	del df_users["Starting Location"]
	del df_users["EON Server Poll Interval (milliseconds)"]
	del df_users["EON Notification Template"]
	del df_users["EON Non-Emergency Notification Template"]
	del df_users["EON Server Stale Notification Threshold (minutes)"]
	del df_users["EON Building Filter Criteria (comma separated)"]
	del df_users["EON Call Server Filter Criteria (comma separated)"]
	#* 2 Filter only mye911 users
	df_users = df_users[df_users['Role'] == "MyE911 User"]

	#* 3 Load mye911 device mappings csv file
	df_maps = pd.read_csv(fname_maps)
	print(f"File loaded successfully: {fname_maps}")
	# Rename username column
	df_maps.rename({'## MyE911 Username': 'Username'}, axis='columns', inplace=True)
	df_maps.rename({'Device Identifier': 'Existing Device Map'}, axis='columns', inplace=True)
	# Delete unnecessary columns
	del df_maps["PBX Name"]

	#* 4 Verify mye911 users have a device mapped
	# Left merge the dataframes, this will fill in device mappings to any user that has a mapping, almost like an excel vlookup
	df_merge = pd.merge(df_users, df_maps, on ='Username', how ='left')
	df_merge.sort_values(by=["Username"], ascending=True, inplace=True)
	df_merge["Found Device Map"] = None

	#* 5 Load all devices csv file
	df_devices = pd.read_csv(fname_devices)
	print(f"File loaded successfully: {fname_devices}")
	# Rename username column
	df_devices.rename({'## Device Name': 'Device Name'}, axis='columns', inplace=True)
	# Delete unnecessary columns
	# del df_devices["PBX Name"]

	#* 6 Iterate over merged dataframe, look for null in Device Mapping column, then search through devices dataframe for match
	for index, row in df_merge.iterrows():
		if type(row["Existing Device Map"]) == float: # if column is NULL / np.nan (float)
			d_match = df_devices.loc[df_devices["Device Name"] == "CSF"+row["Username"]]
			# print(type(d_match))
			# print(d_match)
			if d_match.empty:
				# print("No match for "+row["Username"])
				pass
			else:
				if d_match.shape[0] >= 2:
					print("Multiple matches for "+row["Username"])
				else:
					# print("Match found "+str(d_match.iloc[0]["Device Name"]))
					#! WRITE MATCH INFO INTO MERGE DF
					df_merge.loc[index, "Found Device Map"] = str(d_match.iloc[0]["Device Name"])


	print("\nGenerating report...")
	stat_users_total          = len(df_merge.index)
	stat_users_with_device    = len(df_merge[df_merge["Existing Device Map"].notnull()])
	stat_users_without_device = len(df_merge[df_merge["Existing Device Map"].isnull()])
	stat_devices_available    = len(df_merge[df_merge["Found Device Map"].notnull()])
	print(f"Total MyE911 Users: {stat_users_total}")
	print(f"Users with a device mapped: {stat_users_with_device}")
	print(f"Users without a device mapped: {stat_users_without_device}")
	print(f"Devices matched to users without a device: {stat_devices_available}")
	# print(df_merge)

	# Create a Pandas Excel writer using XlsxWriter as the engine.
	writer = pd.ExcelWriter(fname_output_fol+fname_output, engine='xlsxwriter')
	# Convert the dataframe to an XlsxWriter Excel object.
	df_merge.to_excel(writer, sheet_name='Sheet1', index=False)
	# Get the xlsxwriter workbook and worksheet objects.
	workbook  = writer.book
	worksheet = writer.sheets['Sheet1']
	# Add some cell formats.
	format_text = workbook.add_format({'num_format': '@'}) # @ is text format in excel
	# Set the format but not the column width.
	worksheet.set_column('A:A', 22)
	worksheet.set_column('B:B', 36)
	worksheet.set_column('C:C', 14)
	worksheet.set_column('D:D', 14)
	worksheet.set_column('E:E', 12)
	worksheet.set_column('F:F', 11, format_text)
	worksheet.set_column('G:G', 21)
	worksheet.set_column('H:H', 21)
	af_range = "A1:H"+str(df_merge.shape[0]+1)
	worksheet.autofilter(af_range)
	# worksheet.auto_filter.add_filter_column(1, ['INVALID'], blank=False)
	# Close the Pandas Excel writer and output the Excel file.
	writer.save()
	# csv_set.save(writer.save())
	print(f"Report saved as: {fname_output}")

	if stat_devices_available > 0:
		df_merge.reset_index(inplace = True, drop = True)
		indexes_to_drop = []
		for index, row in df_merge.iterrows():
			# print(f"Type={type(row['Found Device Map'])}, Value={row['Found Device Map']}")
			if type(row["Found Device Map"]) == NoneType:
				# print("removing null")
				indexes_to_drop.append(index)
		df_merge.drop(df_merge.index[indexes_to_drop], inplace=True)

		# Delete uneccessary columns for the bulk CSV import file
		del df_merge["Email"]
		del df_merge["First Name"]
		del df_merge["Last Name"]
		del df_merge["Role"]
		del df_merge["ELIN"]
		del df_merge["Existing Device Map"]

		df_merge.rename({'Username': 'MyE911 Username'}, axis='columns', inplace=True)
		df_merge.rename({'Found Device Map': 'Device Identifier'}, axis='columns', inplace=True)

		df_merge["PBX Name"] = pbx_name

		df_merge.to_csv(fname_output_fol+fname_bulk_output, index=False)
		print(f"Bulk Import file saved as: {fname_bulk_output}")

	return [stat_users_total, stat_users_with_device, stat_users_without_device, stat_devices_available, fname_output, fname_bulk_output]

if __name__ == "__main__":
	app.run(debug=True, host='0.0.0.0', port=5001)