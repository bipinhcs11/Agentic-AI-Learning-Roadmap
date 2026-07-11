# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from app.scheduler import recommend_delivery_windows


def test_recommend_delivery_windows_for_standard_zone() -> None:
    result = recommend_delivery_windows(zip_code="10001", requested_day="Friday")
    assert result["status"] == "success"
    assert result["available_windows"] == ["10:00-12:00", "16:00-18:00"]
