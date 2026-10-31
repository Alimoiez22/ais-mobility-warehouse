# Raw AIS data profile

Table `staging.ais_raw`, generated 2026-10-29 22:46 UTC by `scripts/profile.py`.
All counts are measured on the full table. Nothing has been removed yet.

## 1. Overview

| Measure | Value |
|---|---|
| Rows | 15,808,081 |
| Distinct MMSI (transmitter IDs) | 3,218 |
| Distinct 'Type of mobile' values | 7 |

Rows by type of mobile (what kind of transmitter sent the report):

| Type of mobile | Rows | % of rows | Distinct MMSI |
|---|---|---|---|
| Class A | 13,991,418 | 88.51% | 2,088 |
| Base Station | 964,757 | 6.10% | 45 |
| Class B | 588,747 | 3.72% | 1,368 |
| AtoN | 258,862 | 1.64% | 160 |
| SAR Airborne | 4,210 | 0.03% | 5 |
| Search and Rescue Transponder | 55 | 0.00% | 6 |
| Emergency PIRB | 32 | 0.00% | 7 |

## 2. Completeness

Missing information appears in two forms: an empty field (loaded as NULL) or a
placeholder word ('Unknown', 'Undefined', 'Unknown value').

| Column | NULL | Empty string | Placeholder | Missing in any form |
|---|---|---|---|---|
| `ts` | 0 | 0 | 0 | 0.00% |
| `type_of_mobile` | 0 | 0 | 0 | 0.00% |
| `mmsi` | 0 | 0 | 0 | 0.00% |
| `latitude` | 0 | 0 | 0 | 0.00% |
| `longitude` | 0 | 0 | 0 | 0.00% |
| `nav_status` | 0 | 0 | 2,700,407 | 17.08% |
| `rot` | 5,205,537 | 0 | 0 | 32.93% |
| `sog` | 1,272,066 | 0 | 0 | 8.05% |
| `cog` | 2,260,662 | 0 | 0 | 14.30% |
| `heading` | 3,464,325 | 0 | 0 | 21.91% |
| `imo` | 0 | 0 | 6,770,340 | 42.83% |
| `callsign` | 0 | 0 | 1,517,371 | 9.60% |
| `name` | 1,177,828 | 0 | 0 | 7.45% |
| `ship_type` | 0 | 0 | 1,615,157 | 10.22% |
| `cargo_type` | 13,072,359 | 0 | 0 | 82.69% |
| `width` | 1,607,216 | 0 | 0 | 10.17% |
| `length` | 1,612,858 | 0 | 0 | 10.20% |
| `pos_fixing_device` | 0 | 0 | 1,211,543 | 7.66% |
| `draught` | 4,455,228 | 0 | 0 | 28.18% |
| `destination` | 0 | 0 | 4,371,654 | 27.65% |
| `eta` | 6,045,320 | 0 | 0 | 38.24% |
| `data_source_type` | 0 | 0 | 0 | 0.00% |
| `dim_a` | 1,645,449 | 0 | 0 | 10.41% |
| `dim_b` | 1,820,848 | 0 | 0 | 11.52% |
| `dim_c` | 1,724,215 | 0 | 0 | 10.91% |
| `dim_d` | 1,839,018 | 0 | 0 | 11.63% |

## 3. Numeric fields

Values are text in staging. 'Not a number' counts values that are present but cannot be
read as a number. 'Out of range' counts numbers outside the valid range shown, and it
includes the AIS 'not available' code where that code lies outside the range
(for example heading 511). The valid ranges and codes follow the AIS message standard
(ITU-R M.1371); `rot` is the value as delivered in the file.

| Column | Unit | Valid range | Not a number | Min | Max | Out of range | 'Not available' code: rows |
|---|---|---|---|---|---|---|---|
| `latitude` | degrees | -90 to 90 | 0 | -64.913 | 91 | 20,268 | 91: 20,268 |
| `longitude` | degrees | -180 to 180 | 0 | -9.762 | 135.350 | 0 | 181: 0 |
| `sog` | knots | 0 to 102.2 | 0 | 0 | 201 | 2,467 | 102.3: 0 |
| `cog` | degrees | 0 to 359.9 | 0 | 0 | 359.900 | 0 | 360: 0 |
| `heading` | degrees | 0 to 359 | 0 | 0 | 422 | 2 | 511: 0 |
| `rot` | degrees/min | -720 to 720 | 0 | -708.700 | 708.700 | 0 |  |
| `draught` | metres | 0 to 25.5 | 0 | 0.100 | 25.500 | 0 |  |
| `width` | metres | 0 to 63 | 0 | 1 | 106 | 85,498 |  |
| `length` | metres | 0 to 511 | 0 | 2 | 556 | 5,960 |  |

## 4. Timestamps

Format in the file: `dd/mm/yyyy hh:mm:ss`. The time zone is not stated in the row itself.

| Measure | Value |
|---|---|
| NULL | 0 |
| Present but not in the expected format | 0 |
| Earliest | 2026-10-26 00:00:00 |
| Latest | 2026-10-26 23:59:58 |
| Outside 26 Oct 2026 | 0 |

Rows per hour of the day:

| Hour | Rows | % of rows |
|---|---|---|
| 00 | 637,285 | 4.03% |
| 01 | 640,846 | 4.05% |
| 02 | 641,301 | 4.06% |
| 03 | 644,830 | 4.08% |
| 04 | 650,568 | 4.12% |
| 05 | 663,142 | 4.19% |
| 06 | 684,722 | 4.33% |
| 07 | 678,173 | 4.29% |
| 08 | 668,375 | 4.23% |
| 09 | 656,568 | 4.15% |
| 10 | 655,683 | 4.15% |
| 11 | 662,236 | 4.19% |
| 12 | 649,509 | 4.11% |
| 13 | 642,867 | 4.07% |
| 14 | 664,068 | 4.20% |
| 15 | 673,714 | 4.26% |
| 16 | 682,078 | 4.31% |
| 17 | 675,270 | 4.27% |
| 18 | 665,080 | 4.21% |
| 19 | 659,222 | 4.17% |
| 20 | 657,312 | 4.16% |
| 21 | 641,091 | 4.06% |
| 22 | 655,319 | 4.15% |
| 23 | 658,822 | 4.17% |

## 5. MMSI identifiers

An MMSI is a 9-digit radio identity. By the ITU numbering scheme, ships normally start
with a country code 2-7; other prefixes are used for coast stations (00), SAR aircraft
(111), safety devices (97), craft associated with a parent ship (98) and aids to
navigation (99). This table only counts patterns; it does not judge them.

| Pattern | Rows | % of rows | Distinct MMSI |
|---|---|---|---|
| 9 digits, starts 2-7 | 14,455,095 | 91.44% | 2,986 |
| digits, length 7 | 981,391 | 6.21% | 44 |
| 9 digits, starts 99 | 251,224 | 1.59% | 159 |
| 9 digits, starts 111 | 73,836 | 0.47% | 9 |
| digits, length 4 | 45,382 | 0.29% | 2 |
| 9 digits, other start | 1,066 | 0.01% | 5 |
| 9 digits, starts 97 | 87 | 0.00% | 13 |

## 6. Duplicates

| Kind | Extra rows (beyond the first copy) | % of rows |
|---|---|---|
| Exact duplicates (all 26 columns identical) | 6,076,234 | 38.44% |
| Same MMSI and same timestamp (other columns may differ) | 6,145,107 | 38.87% |

Exact duplicates are a subset of same-MMSI-same-timestamp rows.

## 7. Top values of categorical columns

### `type_of_mobile` (top 15)

| Value | Rows | % of rows |
|---|---|---|
| Class A | 13,991,418 | 88.51% |
| Base Station | 964,757 | 6.10% |
| Class B | 588,747 | 3.72% |
| AtoN | 258,862 | 1.64% |
| SAR Airborne | 4,210 | 0.03% |
| Search and Rescue Transponder | 55 | 0.00% |
| Emergency PIRB | 32 | 0.00% |

### `nav_status` (top 15)

| Value | Rows | % of rows |
|---|---|---|
| Under way using engine | 9,501,312 | 60.10% |
| Unknown value | 2,700,407 | 17.08% |
| Engaged in fishing | 2,115,442 | 13.38% |
| Moored | 463,865 | 2.93% |
| Restricted maneuverability | 323,531 | 2.05% |
| Under way sailing | 212,660 | 1.35% |
| Constrained by her draught | 173,701 | 1.10% |
| At anchor | 120,892 | 0.76% |
| Reserved for future amendment [HSC] | 115,853 | 0.73% |
| Power-driven vessel towing astern | 37,269 | 0.24% |
| Reserved for future amendment [WIG] | 21,821 | 0.14% |
| Reserved for future use | 15,863 | 0.10% |
| Not under command | 5,465 | 0.03% |

### `ship_type` (top 15)

| Value | Rows | % of rows |
|---|---|---|
| Cargo | 3,493,147 | 22.10% |
| Fishing | 3,355,958 | 21.23% |
| Passenger | 1,890,351 | 11.96% |
| Undefined | 1,615,157 | 10.22% |
| Tanker | 1,585,187 | 10.03% |
| Other | 641,962 | 4.06% |
| Pilot | 633,089 | 4.00% |
| Tug | 544,941 | 3.45% |
| SAR | 496,121 | 3.14% |
| Pleasure | 318,484 | 2.01% |
| Dredging | 296,150 | 1.87% |
| HSC | 276,598 | 1.75% |
| Sailing | 231,064 | 1.46% |
| Military | 138,297 | 0.87% |
| Reserved | 66,052 | 0.42% |

### `pos_fixing_device` (top 15)

| Value | Rows | % of rows |
|---|---|---|
| GPS | 12,216,350 | 77.28% |
| Undefined | 1,211,543 | 7.66% |
| Internal | 1,185,080 | 7.50% |
| Combined GPS/GLONASS | 751,137 | 4.75% |
| Surveyed | 410,951 | 2.60% |
| GLONASS | 17,795 | 0.11% |
| Integrated navigation system | 8,195 | 0.05% |
| Galileo | 7,030 | 0.04% |

### `data_source_type` (top 15)

| Value | Rows | % of rows |
|---|---|---|
| AIS | 15,808,081 | 100.00% |

## Query timings

| Query | Seconds |
|---|---|
| overview | 26.9 |
| type_of_mobile | 18.9 |
| completeness | 14.8 |
| numeric | 147.1 |
| timestamps | 70.0 |
| rows_per_hour | 15.2 |
| mmsi | 23.2 |
| duplicates | 259.3 |
| top_type_of_mobile | 4.0 |
| top_nav_status | 3.9 |
| top_ship_type | 4.0 |
| top_pos_fixing_device | 3.2 |
| top_data_source_type | 4.1 |

Total: 595 s.
