from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


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
	sender = frappe.db.get_value("Email Setting",{"email_name": "Purchase Order Email"},"email_id") 
	recipient = doc.contact_email
	if recipient:
		frappe.sendmail(
			sender = sender,
			recipients = recipient,
			subject = "Purchase Invoice : {0}".format(doc.name),
			message = "Purchase Invoice:  " + "https://uatrushabhinstruments.indictranstech.com/app/purchase-invoice/{0}".format(doc.name),
			attachments = file_att,
			)
def validate(doc,method):
	if not doc.get("__islocal"):
		frappe.db.sql("""DELETE from `tabFile` where attached_to_doctype='Purchase Invoice' and attached_to_name=%s""",
			(doc.name))
		pdf_data=frappe.attach_print('Purchase Invoice',doc.name, print_format='Purchase Invoice v1')
		
		_file = frappe.get_doc({
		"doctype": "File",
		"file_name": pdf_data.get('fname'),
		"attached_to_doctype": "Purchase Invoice",
		"attached_to_name": doc.name,
		"is_private": 1,
		"content": pdf_data.get('fcontent')
		})
		_file.save()