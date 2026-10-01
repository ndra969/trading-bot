// GENERATED oleh sdbot/tools/schema.py — jangan diedit. Sumber: shared/schema/enums.md
#ifndef SDB_CORE_SCHEMAENUMS_MQH
#define SDB_CORE_SCHEMAENUMS_MQH

// direction: signals.direction, trades.direction
#define SDB_DIRECTION_BUY "BUY"
#define SDB_DIRECTION_SELL "SELL"

// deal_type: deals.deal_type
#define SDB_DEAL_TYPE_BUY "BUY"
#define SDB_DEAL_TYPE_SELL "SELL"

// session_mode: sessions.mode
#define SDB_SESSION_MODE_LIVE "LIVE"
#define SDB_SESSION_MODE_TESTER "TESTER"

// account_type: accounts.account_type
#define SDB_ACCOUNT_TYPE_DEMO "DEMO"
#define SDB_ACCOUNT_TYPE_REAL "REAL"
#define SDB_ACCOUNT_TYPE_CENT "CENT"

// margin_mode: accounts.margin_mode
#define SDB_MARGIN_MODE_HEDGING "HEDGING"
#define SDB_MARGIN_MODE_NETTING "NETTING"
#define SDB_MARGIN_MODE_EXCHANGE "EXCHANGE"

// trading_style: signals.style
#define SDB_TRADING_STYLE_SCALPING "SCALPING"
#define SDB_TRADING_STYLE_DAY "DAY"
#define SDB_TRADING_STYLE_SWING "SWING"
#define SDB_TRADING_STYLE_POSITION "POSITION"

// signal_status: signals.status
#define SDB_SIGNAL_STATUS_ACCEPTED "ACCEPTED"
#define SDB_SIGNAL_STATUS_REJECTED "REJECTED"

// trade_source: trades.source
#define SDB_TRADE_SOURCE_EA "EA"
#define SDB_TRADE_SOURCE_RECONCILED "RECONCILED"

// deal_entry: deals.entry
#define SDB_DEAL_ENTRY_IN "IN"
#define SDB_DEAL_ENTRY_OUT "OUT"
#define SDB_DEAL_ENTRY_INOUT "INOUT"
#define SDB_DEAL_ENTRY_OUT_BY "OUT_BY"

// balance_op_type: balance_ops.op_type
#define SDB_BALANCE_OP_TYPE_BALANCE "BALANCE"
#define SDB_BALANCE_OP_TYPE_CREDIT "CREDIT"

// severity: alerts.severity
#define SDB_SEVERITY_INFO "INFO"
#define SDB_SEVERITY_MEDIUM "MEDIUM"
#define SDB_SEVERITY_HIGH "HIGH"
#define SDB_SEVERITY_CRITICAL "CRITICAL"

// alert_status: alerts.status
#define SDB_ALERT_STATUS_PENDING "PENDING"
#define SDB_ALERT_STATUS_SENT "SENT"
#define SDB_ALERT_STATUS_FAILED "FAILED"
#define SDB_ALERT_STATUS_SKIPPED "SKIPPED"

// close_reason: closures.reason
#define SDB_CLOSE_REASON_TP "TP"
#define SDB_CLOSE_REASON_SL "SL"
#define SDB_CLOSE_REASON_BE_STOP "BE_STOP"
#define SDB_CLOSE_REASON_TRAIL_STOP "TRAIL_STOP"
#define SDB_CLOSE_REASON_MANUAL "MANUAL"
#define SDB_CLOSE_REASON_STOP_OUT "STOP_OUT"
#define SDB_CLOSE_REASON_EA_CLOSE "EA_CLOSE"
#define SDB_CLOSE_REASON_ROLLOVER "ROLLOVER"
#define SDB_CLOSE_REASON_OTHER "OTHER"

// deal_reason: deals.reason
#define SDB_DEAL_REASON_CLIENT "CLIENT"
#define SDB_DEAL_REASON_MOBILE "MOBILE"
#define SDB_DEAL_REASON_WEB "WEB"
#define SDB_DEAL_REASON_EXPERT "EXPERT"
#define SDB_DEAL_REASON_SL "SL"
#define SDB_DEAL_REASON_TP "TP"
#define SDB_DEAL_REASON_SO "SO"
#define SDB_DEAL_REASON_ROLLOVER "ROLLOVER"
#define SDB_DEAL_REASON_VMARGIN "VMARGIN"
#define SDB_DEAL_REASON_SPLIT "SPLIT"
#define SDB_DEAL_REASON_OTHER "OTHER"

// position_event: position_events.type
#define SDB_POSITION_EVENT_BE "BE"
#define SDB_POSITION_EVENT_PARTIAL "PARTIAL"
#define SDB_POSITION_EVENT_PARTIAL_SKIPPED "PARTIAL_SKIPPED"
#define SDB_POSITION_EVENT_TRAILING "TRAILING"
#define SDB_POSITION_EVENT_MODIFY_FAILED "MODIFY_FAILED"
#define SDB_POSITION_EVENT_SL_RESTORED "SL_RESTORED"

// reject_stage: signals.reject_stage
#define SDB_REJECT_STAGE_STOPPED "STOPPED"
#define SDB_REJECT_STAGE_DAILY_PAUSE "DAILY_PAUSE"
#define SDB_REJECT_STAGE_NOT_TRADABLE "NOT_TRADABLE"
#define SDB_REJECT_STAGE_MAX_OPEN_RISK "MAX_OPEN_RISK"
#define SDB_REJECT_STAGE_CLASS_POSITION_LIMIT "CLASS_POSITION_LIMIT"
#define SDB_REJECT_STAGE_MARGIN_LOW "MARGIN_LOW"
#define SDB_REJECT_STAGE_CURRENCY_EXPOSURE "CURRENCY_EXPOSURE"
#define SDB_REJECT_STAGE_NEWS_BLACKOUT "NEWS_BLACKOUT"
#define SDB_REJECT_STAGE_OUTSIDE_SESSION "OUTSIDE_SESSION"
#define SDB_REJECT_STAGE_SPREAD_TOO_WIDE "SPREAD_TOO_WIDE"
#define SDB_REJECT_STAGE_NO_HTF_BIAS "NO_HTF_BIAS"
#define SDB_REJECT_STAGE_NO_VALID_ZONE "NO_VALID_ZONE"
#define SDB_REJECT_STAGE_ZONE_USED "ZONE_USED"
#define SDB_REJECT_STAGE_NO_PA_TRIGGER "NO_PA_TRIGGER"
#define SDB_REJECT_STAGE_SCORE_TOO_LOW "SCORE_TOO_LOW"
#define SDB_REJECT_STAGE_RR_TOO_LOW "RR_TOO_LOW"
#define SDB_REJECT_STAGE_SL_TOO_CLOSE "SL_TOO_CLOSE"
#define SDB_REJECT_STAGE_INVALID_STOPS "INVALID_STOPS"
#define SDB_REJECT_STAGE_INVALID_VOLUME "INVALID_VOLUME"
#define SDB_REJECT_STAGE_LOT_BELOW_MIN "LOT_BELOW_MIN"
#define SDB_REJECT_STAGE_RISK_PER_TRADE "RISK_PER_TRADE"
#define SDB_REJECT_STAGE_BROKER_REJECTED "BROKER_REJECTED"
#define SDB_REJECT_STAGE_OTHER "OTHER"

// alert_type: alerts.type
#define SDB_ALERT_TYPE_ACCOUNT_REJECTED "ACCOUNT_REJECTED"
#define SDB_ALERT_TYPE_CONN_DOWN "CONN_DOWN"
#define SDB_ALERT_TYPE_CONN_UP "CONN_UP"
#define SDB_ALERT_TYPE_DB_UNAVAILABLE "DB_UNAVAILABLE"
#define SDB_ALERT_TYPE_DB_RECOVERED "DB_RECOVERED"
#define SDB_ALERT_TYPE_DB_NEWER_SCHEMA "DB_NEWER_SCHEMA"
#define SDB_ALERT_TYPE_MIGRATION_FAILED "MIGRATION_FAILED"
#define SDB_ALERT_TYPE_ORDER_FAILED "ORDER_FAILED"
#define SDB_ALERT_TYPE_MODIFY_FAILED "MODIFY_FAILED"
#define SDB_ALERT_TYPE_DD_INFO "DD_INFO"
#define SDB_ALERT_TYPE_DD_REDUCE "DD_REDUCE"
#define SDB_ALERT_TYPE_DD_RECOVERED "DD_RECOVERED"
#define SDB_ALERT_TYPE_DD_STOP "DD_STOP"
#define SDB_ALERT_TYPE_DAILY_LOSS "DAILY_LOSS"
#define SDB_ALERT_TYPE_MARGIN_LOW "MARGIN_LOW"
#define SDB_ALERT_TYPE_MARGIN_OK "MARGIN_OK"
#define SDB_ALERT_TYPE_CLOSE_ALL_FAILED "CLOSE_ALL_FAILED"
#define SDB_ALERT_TYPE_EMERGENCY_RESET "EMERGENCY_RESET"
#define SDB_ALERT_TYPE_BALANCE_OP "BALANCE_OP"
#define SDB_ALERT_TYPE_STATE_RESET "STATE_RESET"
#define SDB_ALERT_TYPE_SL_RESTORED "SL_RESTORED"
#define SDB_ALERT_TYPE_BE_MOVED "BE_MOVED"
#define SDB_ALERT_TYPE_PARTIAL_CLOSED "PARTIAL_CLOSED"
#define SDB_ALERT_TYPE_SL_MISSING "SL_MISSING"
#define SDB_ALERT_TYPE_TRADE_OPENED "TRADE_OPENED"
#define SDB_ALERT_TYPE_TRADE_CLOSED "TRADE_CLOSED"

// alert_status_reason: alerts.status_reason
#define SDB_ALERT_STATUS_REASON_COOLDOWN "COOLDOWN"
#define SDB_ALERT_STATUS_REASON_QUOTA "QUOTA"
#define SDB_ALERT_STATUS_REASON_STALE "STALE"
#define SDB_ALERT_STATUS_REASON_OVERFLOW "OVERFLOW"
#define SDB_ALERT_STATUS_REASON_RESTART "RESTART"
#define SDB_ALERT_STATUS_REASON_TRANSPORT_TEMP "TRANSPORT_TEMP"
#define SDB_ALERT_STATUS_REASON_TRANSPORT_PERMANENT "TRANSPORT_PERMANENT"

// deinit_reason: sessions.end_reason
#define SDB_DEINIT_REASON_PROGRAM "PROGRAM"
#define SDB_DEINIT_REASON_REMOVE "REMOVE"
#define SDB_DEINIT_REASON_RECOMPILE "RECOMPILE"
#define SDB_DEINIT_REASON_CHARTCHANGE "CHARTCHANGE"
#define SDB_DEINIT_REASON_CHARTCLOSE "CHARTCLOSE"
#define SDB_DEINIT_REASON_PARAMETERS "PARAMETERS"
#define SDB_DEINIT_REASON_ACCOUNT "ACCOUNT"
#define SDB_DEINIT_REASON_TEMPLATE "TEMPLATE"
#define SDB_DEINIT_REASON_INITFAILED "INITFAILED"
#define SDB_DEINIT_REASON_CLOSE "CLOSE"
#define SDB_DEINIT_REASON_OTHER "OTHER"

// true bila value adalah nilai sah enum enumName (nama seperti di enums.md).
bool SdbEnumIsValid(const string enumName, const string value)
  {
   if(enumName == "direction")
      return value == "BUY" || value == "SELL";
   if(enumName == "deal_type")
      return value == "BUY" || value == "SELL";
   if(enumName == "session_mode")
      return value == "LIVE" || value == "TESTER";
   if(enumName == "account_type")
      return value == "DEMO" || value == "REAL" || value == "CENT";
   if(enumName == "margin_mode")
      return value == "HEDGING" || value == "NETTING" || value == "EXCHANGE";
   if(enumName == "trading_style")
      return value == "SCALPING" || value == "DAY" || value == "SWING" || value == "POSITION";
   if(enumName == "signal_status")
      return value == "ACCEPTED" || value == "REJECTED";
   if(enumName == "trade_source")
      return value == "EA" || value == "RECONCILED";
   if(enumName == "deal_entry")
      return value == "IN" || value == "OUT" || value == "INOUT" || value == "OUT_BY";
   if(enumName == "balance_op_type")
      return value == "BALANCE" || value == "CREDIT";
   if(enumName == "severity")
      return value == "INFO" || value == "MEDIUM" || value == "HIGH" || value == "CRITICAL";
   if(enumName == "alert_status")
      return value == "PENDING" || value == "SENT" || value == "FAILED" || value == "SKIPPED";
   if(enumName == "close_reason")
      return value == "TP" || value == "SL" || value == "BE_STOP" || value == "TRAIL_STOP" || value == "MANUAL" || value == "STOP_OUT" || value == "EA_CLOSE" || value == "ROLLOVER" || value == "OTHER";
   if(enumName == "deal_reason")
      return value == "CLIENT" || value == "MOBILE" || value == "WEB" || value == "EXPERT" || value == "SL" || value == "TP" || value == "SO" || value == "ROLLOVER" || value == "VMARGIN" || value == "SPLIT" || value == "OTHER";
   if(enumName == "position_event")
      return value == "BE" || value == "PARTIAL" || value == "PARTIAL_SKIPPED" || value == "TRAILING" || value == "MODIFY_FAILED" || value == "SL_RESTORED";
   if(enumName == "reject_stage")
      return value == "STOPPED" || value == "DAILY_PAUSE" || value == "NOT_TRADABLE" || value == "MAX_OPEN_RISK" || value == "CLASS_POSITION_LIMIT" || value == "MARGIN_LOW" || value == "CURRENCY_EXPOSURE" || value == "NEWS_BLACKOUT" || value == "OUTSIDE_SESSION" || value == "SPREAD_TOO_WIDE" || value == "NO_HTF_BIAS" || value == "NO_VALID_ZONE" || value == "ZONE_USED" || value == "NO_PA_TRIGGER" || value == "SCORE_TOO_LOW" || value == "RR_TOO_LOW" || value == "SL_TOO_CLOSE" || value == "INVALID_STOPS" || value == "INVALID_VOLUME" || value == "LOT_BELOW_MIN" || value == "RISK_PER_TRADE" || value == "BROKER_REJECTED" || value == "OTHER";
   if(enumName == "alert_type")
      return value == "ACCOUNT_REJECTED" || value == "CONN_DOWN" || value == "CONN_UP" || value == "DB_UNAVAILABLE" || value == "DB_RECOVERED" || value == "DB_NEWER_SCHEMA" || value == "MIGRATION_FAILED" || value == "ORDER_FAILED" || value == "MODIFY_FAILED" || value == "DD_INFO" || value == "DD_REDUCE" || value == "DD_RECOVERED" || value == "DD_STOP" || value == "DAILY_LOSS" || value == "MARGIN_LOW" || value == "MARGIN_OK" || value == "CLOSE_ALL_FAILED" || value == "EMERGENCY_RESET" || value == "BALANCE_OP" || value == "STATE_RESET" || value == "SL_RESTORED" || value == "BE_MOVED" || value == "PARTIAL_CLOSED" || value == "SL_MISSING" || value == "TRADE_OPENED" || value == "TRADE_CLOSED";
   if(enumName == "alert_status_reason")
      return value == "COOLDOWN" || value == "QUOTA" || value == "STALE" || value == "OVERFLOW" || value == "RESTART" || value == "TRANSPORT_TEMP" || value == "TRANSPORT_PERMANENT";
   if(enumName == "deinit_reason")
      return value == "PROGRAM" || value == "REMOVE" || value == "RECOMPILE" || value == "CHARTCHANGE" || value == "CHARTCLOSE" || value == "PARAMETERS" || value == "ACCOUNT" || value == "TEMPLATE" || value == "INITFAILED" || value == "CLOSE" || value == "OTHER";
   return false;
  }

#endif // SDB_CORE_SCHEMAENUMS_MQH
