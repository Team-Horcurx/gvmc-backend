import re

from wards.wards_service import WardsService
from properties.properties_service import PropertiesService
from stats.stats_service import StatsService
from verify.verify_service import VerifyService
from export.export_service import ExportService
from admin.admin_service import AdminService
from chat.chat_service import ChatService
from tickets.tickets_service import TicketsService

_wards   = WardsService()
_props   = PropertiesService()
_stats   = StatsService()
_verify  = VerifyService()
_export  = ExportService()
_admin   = AdminService()
_chat    = ChatService()
_tickets = TicketsService()

# (METHOD, path_pattern, handler, path_param_names)
ROUTES = [
    ("GET",  r"/api/wards",                                       _wards.list_wards,         []),
    ("GET",  r"/api/wards/(?P<ward_id>[^/]+)/changes",            _wards.get_changes,         ["ward_id"]),
    ("GET",  r"/api/wards/(?P<ward_id>[^/]+)/unassessed",         _wards.get_unassessed,      ["ward_id"]),
    ("GET",  r"/api/wards/(?P<ward_id>[^/]+)/alerts",             _wards.get_alerts,          ["ward_id"]),
    ("GET",  r"/api/stats/all-wards",                             _stats.get_all_wards,       []),
    ("GET",  r"/api/stats",                                       _stats.get_stats,           []),
    ("GET",  r"/api/properties/(?P<property_id>[^/]+)",           _props.get_property,        ["property_id"]),
    ("POST", r"/api/properties/(?P<property_id>[^/]+)/verify",    _verify.update_status,      ["property_id"]),
    ("POST", r"/api/alerts/export",                               _export.export_csv,         []),
    ("POST", r"/api/admin/upload-csv",                            _admin.upload_csv,          []),
    ("POST", r"/api/admin/db-config",                             _admin.db_config,           []),
    ("POST", r"/api/admin/refresh",                               _admin.refresh_pipeline,    []),
    ("POST", r"/api/chat",                                        _chat.chat,                 []),
    ("POST", r"/api/tickets/photo-upload",                        _tickets.get_photo_upload_url, []),
    ("POST", r"/api/tickets",                                     _tickets.create_ticket,        []),
    ("GET",  r"/api/tickets",                                     _tickets.list_tickets,         []),
    ("GET",  r"/api/tickets/(?P<ticket_id>[^/]+)",                _tickets.get_ticket,           ["ticket_id"]),
    ("PATCH",r"/api/tickets/(?P<ticket_id>[^/]+)/review",         _tickets.review_ticket,        ["ticket_id"]),
]


def dispatch(method: str, path: str, obj: dict):
    path = path.rstrip("/") or "/"
    for route_method, pattern, handler, _ in ROUTES:
        if route_method != method:
            continue
        m = re.fullmatch(pattern, path)
        if m:
            return handler(obj, **m.groupdict())
    return 404, {"message": f"No route for {method} {path}"}
