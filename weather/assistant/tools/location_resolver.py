from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedLocation:
    canonical_name: str
    province: str
    latitude: float
    longitude: float


LOCATION_ALIASES: dict[str, ResolvedLocation] = {
    "北京": ResolvedLocation("北京", "北京", 39.9042, 116.4074),
    "beijing": ResolvedLocation("北京", "北京", 39.9042, 116.4074),
    "上海": ResolvedLocation("上海", "上海", 31.2304, 121.4737),
    "shanghai": ResolvedLocation("上海", "上海", 31.2304, 121.4737),
    "广州": ResolvedLocation("广州", "广东", 23.1291, 113.2644),
    "guangzhou": ResolvedLocation("广州", "广东", 23.1291, 113.2644),
    "深圳": ResolvedLocation("深圳", "广东", 22.5431, 114.0579),
    "shenzhen": ResolvedLocation("深圳", "广东", 22.5431, 114.0579),
    "杭州": ResolvedLocation("杭州", "浙江", 30.2741, 120.1551),
    "hangzhou": ResolvedLocation("杭州", "浙江", 30.2741, 120.1551),
    "南京": ResolvedLocation("南京", "江苏", 32.0603, 118.7969),
    "nanjing": ResolvedLocation("南京", "江苏", 32.0603, 118.7969),
    "成都": ResolvedLocation("成都", "四川", 30.5728, 104.0668),
    "chengdu": ResolvedLocation("成都", "四川", 30.5728, 104.0668),
    "重庆": ResolvedLocation("重庆", "重庆", 29.5630, 106.5516),
    "chongqing": ResolvedLocation("重庆", "重庆", 29.5630, 106.5516),
    "武汉": ResolvedLocation("武汉", "湖北", 30.5928, 114.3055),
    "wuhan": ResolvedLocation("武汉", "湖北", 30.5928, 114.3055),
    "西安": ResolvedLocation("西安", "陕西", 34.3416, 108.9398),
    "xian": ResolvedLocation("西安", "陕西", 34.3416, 108.9398),
    "苏州": ResolvedLocation("苏州", "江苏", 31.2989, 120.5853),
    "suzhou": ResolvedLocation("苏州", "江苏", 31.2989, 120.5853),
    "天津": ResolvedLocation("天津", "天津", 39.0842, 117.2009),
    "tianjin": ResolvedLocation("天津", "天津", 39.0842, 117.2009),
}

PROVINCE_ALIASES: dict[str, str] = {
    "北京": "北京",
    "上海": "上海",
    "广东": "广东",
    "浙江": "浙江",
    "江苏": "江苏",
    "四川": "四川",
    "重庆": "重庆",
    "湖北": "湖北",
    "陕西": "陕西",
    "天津": "天津",
}


def resolve_location(query: str) -> ResolvedLocation | None:
    lowered = query.lower()
    for alias, location in sorted(
        LOCATION_ALIASES.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if alias in query or alias in lowered:
            return location
    return None


def resolve_province(query: str) -> str:
    for alias, province in sorted(
        PROVINCE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if alias in query:
            return province
    return ""
