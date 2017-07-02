import re
from functools import partial

from rest_framework.serializers import Serializer, ModelSerializer, Field

class PermissionField(Field):
	def __init__(self, *args, **kwargs):
		kwargs["read_only"] = True
		super(PermissionField, self).__init__(*args, **kwargs)

	def to_representation(self, obj):
		request = self.context["request"]
		permission_methods = filter(lambda method: re.match("can_", method), dir(obj))
		permissions = []
		for permission_method in permission_methods:
			permission_name = permission_method.replace("can_", "")
			authorizer = getattr(obj, permission_method)
			if authorizer(request.user, request):
				permissions.append(permission_name)
		return permissions

	def get_attribute(self, instance):
		return instance

class SaneSerializerMixin:
	def __init__(self, *args, **kwargs):
		super(SaneSerializerMixin, self).__init__(*args, **kwargs)

		if not self.context or not self.context.get("request"):
			return

		request = self.context.get("request")
		request_method = request.method.lower()
		available_fields = set(self.fields.keys())

		accessible_fields, requested_fields = None, None
		if request_method == "get":
			accessible_fields = set(self.get_readable_fields())
			fields_str = request.query_params.get("fields")
			if fields_str:
				requested_fields = set(fields_str.split(","))
		else:
			accessible_fields = set(self.get_writable_fields())

		field_groups = [available_fields, accessible_fields, requested_fields]
		valid_field_groups = filter(lambda group: not not group, field_groups)
		final_fields = set.intersection(*valid_field_groups)

		for field in available_fields - final_fields:
			self.fields.pop(field)


class SaneSerializer(SaneSerializerMixin, Serializer):
	pass

class SaneModelSerializer(SaneSerializerMixin, ModelSerializer):
	permissions = PermissionField()