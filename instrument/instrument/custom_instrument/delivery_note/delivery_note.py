from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
import requests
def on_submit(doc, method = None):
	file_att = []
	file_att = [frappe.attach_print(doc.doctype, doc.name, file_name=doc.name)]
	attachments = frappe.db.sql(""" SELECT file_name  FROM tabFile 
				WHERE attached_to_name = '{0}'""".format(doc.name),as_dict=1)
	if attachments:
		for row in attachments:
			_file = frappe.get_doc("File", {"file_name": row.file_name})
			content = _file.get_content()
			if not content:
				return
			attachment_list = {'fname':row.file_name,'fcontent':content}
			file_att.append(attachment_list)
	sender = frappe.db.get_value("Email Setting",{"email_name": "Sales Order Email"},"email_id")
	recipient = doc.contact_email
	if recipient:
		frappe.sendmail(
			sender = sender,
			recipients = recipient,
			subject = "	Delivery Note : {0}".format(doc.name),
			message = "Delivery Note: "+"https://uatrushabhinstruments.indictranstech.com/app/delivery-note/{0}".format(doc.name),
			attachments = file_att,
			)
	custom_api(doc)
def custom_api(doc, event=None):
	items = []
	data = {}
	data.update({'name': doc.name, 'customer': doc.customer, 'customer_name': doc.customer_name, 'company': doc.company,
	            'posting_date': str(doc.posting_date), 'woocommerce_order_id': doc.woocommerce_order_id, 'total_qty': doc.total_qty, 
	            'net_total': doc.net_total, 'status': doc.status})
	if doc.get('items'):
	    for item in doc.items:
	        items.append({'item_code': item.item_code, 'item_name': item.item_name, 'item_group': item.item_group, 'qty': item.qty,
	                    'stock_uom': item.stock_uom, 'conversion_factor': 1.0, 'rate': item.rate, 
	                    'against_sales_order': item.against_sales_order, 'batch_no': item.batch_no, 'serial_no': item.serial_no,'item_expiry_date':str(item.item_expiry_date)})

	    data.update({'items': items})
	path = frappe.db.get_single_value("Rushabh Settings", 'delivery_note_web_hook_url')
	url = path
	frappe.msgprint(str(data))

	response = requests.post(url, data= json.dumps(data))
    
def validate(doc,method):
	if not doc.get("__islocal"):
		frappe.db.sql("""DELETE from `tabFile` where attached_to_doctype='Delivery Note' and attached_to_name=%s""",
			(doc.name))
		pdf_data=frappe.attach_print('Delivery Note',doc.name, print_format='Delivery Note Print')
		
		_file = frappe.get_doc({
		"doctype": "File",
		"file_name": pdf_data.get('fname'),
		"attached_to_doctype": "Delivery Note",
		"attached_to_name": doc.name,
		"is_private": 1,
		"content": pdf_data.get('fcontent')
		})
		_file.save()
	if doc.items:
		for item in doc.items:
			expiry_date = frappe.db.get_value("Batch",{'name':item.batch_no},'expiry_date')
			if expiry_date:
				item.item_expiry_date = expiry_date