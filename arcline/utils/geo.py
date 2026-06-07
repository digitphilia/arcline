# -*- encoding: utf-8 -*-

"""
Geographic Math Helpers
-----------------------

Pure standard-library helpers for the small amount of geographic math
the dashboard and optimization layers need: great-circle distance via
the haversine formula and a tight axis-aligned bounding box over a
list of latitude/longitude pairs.

The module has no third-party dependencies; full geospatial workloads
(geocoding, projections, routing) are explicitly out of scope.
"""

import math
from typing import List, Tuple


EARTH_RADIUS_KM : float = 6371.0088


def haversine(
        lat1 : float, lon1 : float, lat2 : float, lon2 : float
) -> float:
    """
    Great-circle distance between two points on the Earth's surface
    computed via the haversine formula. The Earth is approximated as
    a sphere of radius :data:`EARTH_RADIUS_KM`.

    .. code-block:: python

        haversine(12.97, 77.59, 19.07, 72.87)  # Bangalore -> Mumbai
        # -> ~837.0

    :type  lat1: float
    :param lat1: Latitude of the first point in decimal degrees.

    :type  lon1: float
    :param lon1: Longitude of the first point in decimal degrees.

    :type  lat2: float
    :param lat2: Latitude of the second point in decimal degrees.

    :type  lon2: float
    :param lon2: Longitude of the second point in decimal degrees.

    :rtype:   float
    :returns: Great-circle distance in kilometres.
    """

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return EARTH_RADIUS_KM * c


def bbox(
        points : List[Tuple[float, float]]
) -> Tuple[float, float, float, float]:
    """
    Compute the tight axis-aligned bounding box covering a list of
    ``(latitude, longitude)`` pairs.

    :type  points: List[Tuple[float, float]]
    :param points: Non-empty list of ``(lat, lon)`` pairs in decimal
        degrees.

    :raises ValueError: If ``points`` is empty.

    :rtype:   Tuple[float, float, float, float]
    :returns: ``(min_lat, min_lon, max_lat, max_lon)``.
    """

    if not points:
        raise ValueError(
            "`points` must contain at least one (lat, lon) pair."
        )

    lats = [lat for lat, _ in points]
    lons = [lon for _, lon in points]

    return (min(lats), min(lons), max(lats), max(lons))
