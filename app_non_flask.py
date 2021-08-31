import pandas as pd
import numpy as np
import datetime

'''
Order of operations
1	Load users csv file
2	Filter only mye911 users
3	Load mye911 device mappings csv file
4	Verify mye911 users have a device mapped
'''

fname_users   = input("Enter the users CSV file name: ") or "Users-2020.11.02-11.42.53.csv"
fname_maps    = input("Enter the device mapping CSV file name: ") or "MyE911DeviceMappings-2020.11.02-11.42.40.csv"
fname_devices = input("Enter the all devices CSV file name: ") or "AllDeviceReport-2020.11.02-11.43.10.csv"
fname_output  = "redsky-users-and-devicemappings-"+datetime.datetime.now().strftime("%Y.%m.%d-%I.%M.%S")+".xlsx"

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
df_maps.rename({'Device Identifier': 'Device Mapping'}, axis='columns', inplace=True)
# Delete unnecessary columns
del df_maps["PBX Name"]

#* 4 Verify mye911 users have a device mapped
# Left merge the dataframes, this will fill in device mappings to any user that has a mapping, almost like an excel vlookup
df_merge = pd.merge(df_users, df_maps, on ='Username', how ='left')
df_merge.sort_values(by=["Username"], ascending=True, inplace=True)
df_merge["Mapable"] = None

#* 5 Load all devices csv file
df_devices = pd.read_csv(fname_devices)
print(f"File loaded successfully: {fname_devices}")
# Rename username column
df_devices.rename({'## Device Name': 'Device Name'}, axis='columns', inplace=True)
# Delete unnecessary columns
# del df_devices["PBX Name"]

#* 6 Iterate over merged dataframe, look for null in Device Mapping column, then search through devices dataframe for match
for index, row in df_merge.iterrows():
	if type(row["Device Mapping"]) == float: # if column is NULL / np.nan (float)
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
				df_merge.loc[index, "Mapable"] = "Yes"


print("\nGenerating report...")
stat_users_total          = len(df_merge.index)
stat_users_with_device    = len(df_merge[df_merge["Device Mapping"].notnull()])
stat_users_without_device = len(df_merge[df_merge["Device Mapping"].isnull()])
stat_devices_available    = len(df_merge[df_merge["Mapable"].notnull()])
print(f"Total MyE911 Users: {stat_users_total}")
print(f"Users with a device mapped: {stat_users_with_device}")
print(f"Users without a device mapped: {stat_users_without_device}")
print(f"Devices matched to users without a device: {stat_devices_available}")
# print(df_merge)

# Create a Pandas Excel writer using XlsxWriter as the engine.
writer = pd.ExcelWriter(fname_output, engine='xlsxwriter')
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
worksheet.set_column('G:G', 16)
af_range = "A1:H"+str(df_merge.shape[0]+1)
worksheet.autofilter(af_range)
# worksheet.auto_filter.add_filter_column(1, ['INVALID'], blank=False)
# Close the Pandas Excel writer and output the Excel file.
writer.save()
print(f"Report saved as: {fname_output}")