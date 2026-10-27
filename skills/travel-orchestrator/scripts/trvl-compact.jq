def airport:
  if type == "object" then {code, name} else . end;

def leg:
  {
    departure_airport: (.departure_airport | airport),
    arrival_airport: (.arrival_airport | airport),
    departure_time,
    arrival_time,
    duration,
    stops,
    airline,
    airline_code,
    flight_number,
    direction,
    baggage: (.baggage // .bags // null)
  } | with_entries(select(.value != null and .value != ""));

def common_field:
  . as $key
  | [
      "price", "currency", "provider", "provider_name", "source",
      "itinerary", "departure_date", "return_date", "departure_time",
      "arrival_time", "duration", "stops", "airlines", "airline",
      "booking_url", "bookingUrl", "url", "baggage", "bags", "fare_type",
      "warnings", "legs", "property_name", "hotel_name", "property_id",
      "hotel_id", "address", "room", "room_type", "room_configuration",
      "bed_configuration", "beds", "occupancy", "amenities", "stars",
      "rating", "checkin", "checkout", "check_in", "check_out", "taxes",
      "tax", "fees", "mandatory_fees", "surcharges", "total_price", "total",
      "stay_total", "nightly_price", "price_per_night", "cancellation",
      "cancellation_policy", "refundable", "points", "points_required", "miles",
      "cash_price", "cash_equivalent", "cash_fees", "cpp", "program",
      "program_name", "program_slug", "award_date", "date", "cabin",
      "transfer_route"
    ]
  | index($key) != null;

def offer:
  . as $raw |
  {
    price,
    currency,
    provider,
    source: (.source // .provider_name // null),
    itinerary: (.itinerary // null),
    departure_date,
    return_date,
    departure_time,
    arrival_time,
    duration,
    stops,
    airlines: (.airlines // .airline // null),
    booking_url: (.booking_url // .bookingUrl // .url // null),
    baggage: (.baggage // .bags // null),
    fare_type,
    warnings,
    legs: (if (.legs | type) == "array" then [.legs[] | leg] else null end),
    property_name: (.property_name // .hotel_name // null),
    property_id: (.property_id // .hotel_id // null),
    address,
    room,
    room_type,
    room_configuration: (.room_configuration // .bed_configuration // .beds // null),
    occupancy,
    amenities,
    stars,
    rating,
    checkin: (.checkin // .check_in // null),
    checkout: (.checkout // .check_out // null),
    taxes: (.taxes // .tax // null),
    fees: (.fees // .mandatory_fees // null),
    surcharges,
    total_price: (.total_price // .total // .stay_total // null),
    nightly_price: (.nightly_price // .price_per_night // null),
    cancellation: (.cancellation // .cancellation_policy // null),
    refundable,
    points: (.points // .points_required // .miles // null),
    cash_price: (.cash_price // .cash_equivalent // null),
    cash_fees: (.cash_fees // .taxes // .surcharges // null),
    cpp,
    program: (.program // .program_name // .program_slug // null),
    award_date: (.award_date // .date // null),
    cabin,
    transfer_route,
    details: ($raw | with_entries(select((.key | common_field) | not))
      | if length == 0 then null else . end)
  } | with_entries(select(.value != null and .value != "" and .value != []));

def candidate_arrays:
  . as $root
  | [
      ($root.flights[]?), ($root.itineraries[]?), ($root.offers[]?),
      ($root.results[]?), ($root.dates[]?), ($root.grid[]?), ($root.cells[]?),
      ($root.hotels[]?), ($root.accommodations[]?), ($root.properties[]?),
      ($root.rooms[]?), ($root.awards[]?), ($root.redemptions[]?),
      ($root.award_results[]?), ($root.points_values[]?)
    ];

def candidates:
  . as $root
  | (candidate_arrays | map(select(type == "object"))) as $items
  | if ($items | length) > 0 then $items
    elif (($root | type) == "object"
      and (($root | has("price"))
        or ($root | has("cash_price"))
        or ($root | has("cpp"))
        or ($root | has("points_required"))
        or ($root | has("hotel_name"))
        or ($root | has("property_name")))) then [$root]
    else []
    end;

{
  source: "trvl-cli",
  success,
  count,
  trip_type,
  query: (.query // null),
  searched_at: (.booking_context.searched_at // .searched_at // null),
  provider_status: (.provider_status // .provider_statuses // .providers // .completeness // null),
  error: (.error // .errors // null),
  # Do not rank or truncate here: price may use mixed currencies or scopes.
  # Normalize comparable all-in totals before selecting finalists.
  offers: ([candidates[] | offer])
} | with_entries(select(.value != null and .value != "" and .value != []))
