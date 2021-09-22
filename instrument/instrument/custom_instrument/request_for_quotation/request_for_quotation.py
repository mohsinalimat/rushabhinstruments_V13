from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue
from frappe.desk.form.load import get_attachments


def validate(doc,method):
	if doc.items:
		for item in doc.items:
			engineering_revision = frappe.db.get_value("Item",{'item_code':item.item_code},'engineering_revision')
			item.default_engineering_revision = engineering_revision

def on_submit(doc, method = None):
	file_att = []
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

	send_email_without_reference_to_supplier(doc, method, file_att)
	attach_purchasing_docs(doc,method)

def send_email_without_reference_to_supplier(doc, method, file_att):
	file_att.append(frappe.attach_print("Request for Quotation", doc.name))
	email_template = frappe.get_doc("Email Template", "Request for Quotation")
	data = {}
	for row in doc.suppliers:
		data["salutation"] = doc.salutation
		data["supplier_name"] = row.supplier_name
		data["username"] = frappe.db.get_value("User", {"name":frappe.session.user}, "full_name")
		if row.without_url_email:
			message = frappe.render_template(email_template.response_html, data)
			email_args = {
				"recipients": [row.email_id],
				"sender": frappe.db.get_value("Email Setting",{"email_name": "Purchase Order Email"},"email_id"),
				"subject": email_template.subject,
				"message": message,
				"now": True,
				"expose_recipients": "header",
				"read_receipt": 0,
				"is_notification": False,
				"attachments": file_att
			}
			enqueue(method=frappe.sendmail, queue='short', timeout=300, is_async=True, delayed=False, **email_args)
		data.clear()

@frappe.whitelist()
def get_engineering_revision(item_code):
	if item_code:
		engineering_revision = frappe.db.get_value("Item",{'name':item_code},'engineering_revision')
		return engineering_revision


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_engineering_revisions_for_filter(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(""" SELECT name FROM `tabEngineering Revision` where item_code = '{0}' """.format(filters.get("item_code")))


def attach_purchasing_docs(doc, method):
	for row in doc.items:
		if row.item_code and row.engineering_revision:
			purchasing_package = frappe.db.sql("""SELECT purchasing_package_name from `tabPurchasing Package Table` a join `tabEngineering Revision` b on a.parent = b.name where b.name = '{0}'""".format(row.engineering_revision),as_dict=1,debug=1)
			purchasing_package_list = [item.purchasing_package_name for item in purchasing_package]
			for row in purchasing_package_list:
				package_doc = frappe.get_doc("Package Document",row)
				"""Copy attachments from `package document`"""
				from frappe.desk.form.load import get_attachments

				#loop through attachments
				for attach_item in get_attachments(package_doc.doctype, package_doc.name):

					#save attachments to new doc
					_file = frappe.get_doc({
						"doctype": "File",
						"file_url": attach_item.file_url,
						"file_name": attach_item.file_name,
						"attached_to_name": doc.name,
						"attached_to_doctype": doc.doctype,
						"folder": "Home/Attachments"})
					_file.save()