from mypy.nodes import MemberExpr
from mypy.plugin import AttributeContext, FunctionContext
from mypy.types import AnyType, Instance, TypeOfAny, TypeType
from mypy.types import Type as MypyType

from mypy_django_plugin.django.context import DjangoContext
from mypy_django_plugin.lib import helpers


def get_user_model_hook(ctx: FunctionContext, django_context: DjangoContext) -> MypyType:
    auth_user_model = django_context.settings.AUTH_USER_MODEL
    model_cls = django_context.apps_registry.get_model(auth_user_model)
    model_cls_fullname = helpers.get_class_fullname(model_cls)

    model_info = helpers.lookup_fully_qualified_typeinfo(helpers.get_typechecker_api(ctx), model_cls_fullname)
    if model_info is None:
        return AnyType(TypeOfAny.unannotated)

    return TypeType(Instance(model_info, []))


def get_type_of_settings_attribute(ctx: AttributeContext, django_context: DjangoContext) -> MypyType:
    if not isinstance(ctx.context, MemberExpr):
        return ctx.default_attr_type

    setting_name = ctx.context.name

    typechecker_api = helpers.get_typechecker_api(ctx)

    # first look for the setting in the project settings file, then global settings
    settings_module = typechecker_api.modules.get(django_context.django_settings_module)
    global_settings_module = typechecker_api.modules.get("django.conf.global_settings")
    for module in [settings_module, global_settings_module]:
        if module is not None:
            sym = module.names.get(setting_name)
            if sym is not None:
                if sym.type is None:
                    ctx.api.fail(
                        f"Import cycle from Django settings module prevents type inference for {setting_name!r}",
                        ctx.context,
                    )
                    return ctx.default_attr_type
                return sym.type

    ctx.api.fail(f"'Settings' object has no attribute {setting_name!r}", ctx.context)
    return ctx.default_attr_type
