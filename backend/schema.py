"""Small allowlist shared by validation and the catalog form API."""
from datetime import datetime, date, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from zoneinfo import ZoneInfo
import os
import re
from .errors import require, AppError

# Field spec: type, maximum length (text), nullable, reference table.
def text(n, optional=False): return {'type':'text','max':n,'optional':optional}
def number(scale=2, minimum='0.01'): return {'type':'decimal','scale':scale,'min':minimum}
def ref(table): return {'type':'int','ref':table}
CATALOGS = {
 'Clients': ('ClientID', {'Name':text(120),'Phone':text(30),'Email':text(120,True),'Address':text(250,True)}),
 'Cities': ('CityID', {'Name':text(80)}),
 'VehicleTypes': ('VehicleTypeID', {'Name':text(60)}),
 'Vehicles': ('VehicleID', {'VehicleTypeID':ref('VehicleTypes'),'PlateNumber':text(20),'Brand':text(80),'CapacityKg':number(),'IsActive':{'type':'bool'}}),
 'Drivers': ('DriverID', {'FullName':text(120),'Phone':text(30),'LicenseNumber':text(30),'IsActive':{'type':'bool'}}),
 'Routes': ('RouteID', {'FromCityID':ref('Cities'),'ToCityID':ref('Cities'),'DistanceKm':number()}),
 'CargoTypes': ('CargoTypeID', {'Name':text(80),'Description':text(250,True)}),
 'Tariffs': ('TariffID', {'Name':text(100),'VehicleTypeID':ref('VehicleTypes'),'BasePrice':number(2,'0'),'PricePerKm':number(2,'0'),'PricePerKg':number(2,'0'),'IsActive':{'type':'bool'}})
}


def string(value, maximum, field=None, optional=False):
    if optional and (value is None or value == ''): return None
    require(isinstance(value,str), 'invalid', field=field)
    value = value.strip()
    require(0 < len(value) <= maximum and not any(ord(c)<32 and c not in '\n\t' for c in value), 'text_length', field=field)
    return value


def integer(value, field=None):
    require(not isinstance(value,bool) and re.fullmatch(r'[1-9][0-9]{0,9}',str(value)) is not None, field=field)
    value = int(value)
    require(value <= 2147483647, 'number_range', field=field)
    return value


def dec(value, minimum='0.01', scale=2, field=None):
    try:
        result = Decimal(str(value))
        require(result.is_finite() and Decimal(minimum) <= result <= Decimal('9999999999'), 'number_range', field=field)
        rounded = result.quantize(Decimal(10)**-scale, rounding=ROUND_HALF_UP)
        require(result == rounded, 'decimal_places', field=field)
        return rounded
    except (InvalidOperation, ValueError, TypeError): raise AppError('number_range', field=field) from None


def email(value):
    value = string(value,120,'Email').lower()
    require(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value), 'email', field='Email')
    return value


def password(value):
    require(isinstance(value,str) and 10 <= len(value) <= 128, 'password_length', field='Password')
    return value


def local_zone(): return ZoneInfo(os.getenv('APP_TIMEZONE','Asia/Qyzylorda'))


def local_to_utc(value, field=None):
    try:
        parsed = datetime.fromisoformat(str(value))
        if parsed.tzinfo is None: parsed = parsed.replace(tzinfo=local_zone())
        return parsed.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)
    except (ValueError, TypeError): raise AppError('datetime', field=field) from None


def calendar_date(value, field=None):
    try: return date.fromisoformat(str(value))
    except (ValueError, TypeError): raise AppError('date', field=field) from None


def catalog_payload(table, payload):
    require(table in CATALOGS, 'not_found',404)
    require(isinstance(payload,dict), 'invalid')
    fields = CATALOGS[table][1]
    require(not (set(payload)-set(fields)), 'unknown_field')
    result={}
    for name, spec in fields.items():
        value=payload.get(name)
        kind=spec['type']
        if kind=='text': result[name]=string(value,spec['max'],name,spec.get('optional',False))
        elif kind=='decimal': result[name]=dec(value,spec['min'],spec['scale'],name)
        elif kind=='int': result[name]=integer(value,name)
        else:
            require(value in (True,False,0,1),field=name)
            result[name]=bool(value)
    return result
