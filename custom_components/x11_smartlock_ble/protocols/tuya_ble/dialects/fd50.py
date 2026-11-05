"""Project validated V4 reports onto the model's supported datapoints."""

import time

from ..const import PointType
from ..reports import Report, decode_report


class FD50PayloadDecoder:
    def __init__(self, points, notify, setting_ids, state_flag=47, state_point=118):
        self.setting_ids = setting_ids
        self.state_flag = state_flag
        self.state_point = state_point
        self._datapoints = points
        self._fire_callbacks = notify

    def parse(self, data):
        try:
            report = data if isinstance(data, Report) else decode_report(data)
        except ValueError:
            return
        # Timestamped packets may replay historical events. Until this model's
        # history semantics are known, only live reports update current values.
        if report.source_timestamp is not None:
            return
        updates = []
        received_at = time.time()
        for point_id, kind, raw in report.points:
            if point_id == self.state_flag and kind == PointType.DT_BOOL.value:
                self._datapoints._update_from_device(
                    self.state_point,
                    received_at,
                    self.state_flag,
                    PointType.DT_ENUM,
                    int.from_bytes(raw, "big"),
                )
                updates.append(self._datapoints[self.state_point])
            elif point_id in self.setting_ids and kind in (1, 2, 4):
                self._datapoints._update_from_device(
                    point_id,
                    received_at,
                    0,
                    PointType(kind),
                    int.from_bytes(raw, "big"),
                )
                updates.append(self._datapoints[point_id])
        self._fire_callbacks(updates)
