/**
 * Bridge between the live `/conditions` feed and the Safety / Sea Today / Alerts
 * page shapes.
 *
 * The translated wording in safetyData / seaTodayData / alertsData is kept — it
 * is real, human-written copy in six languages. What these adapters replace is
 * every *fact*: the wave heights, wind speeds, visibility, verdicts, warnings
 * and timestamps that used to be typed in by hand now come from the forecast.
 *
 * Where the live feed has no equivalent for something (a history of past
 * alerts, for instance) the adapter returns an empty list rather than keeping
 * the invented placeholder.
 */

import { LiveAlert, LiveCondition, LiveConditions } from '../services/orcaApi';
import { clockTime, relativeTime } from '../hooks/useConditions';
import type { ConditionItem, SafetyData, SafetyStatus } from './safetyData';
import type { SeaStatus, SeaTodayCondition, SeaTodayData, ForecastHour } from './seaTodayData';
import type { AlertItem, AlertSeverity, AlertsPageData } from './alertsData';

/*
 * Before the forecast arrives — or if it cannot be fetched — these screens must
 * not read as an all-clear. A safety screen that says "SAFE TO GO" or "No
 * important alerts" while it is still loading is telling a fisherman something
 * it does not know, and that is the one failure that could get somebody killed.
 * The helpers below neutralise the reassuring copy until real data backs it.
 */

export function pendingSafety(base: SafetyData, failed: boolean): SafetyData {
  return {
    ...base,
    statusLabel: failed ? 'CONDITIONS UNAVAILABLE' : 'CHECKING…',
    riskSubtitle: failed
      ? 'The forecast could not be loaded.'
      : 'Reading the latest forecast for your area.',
    explanation: failed
      ? 'Do not treat this as an all-clear — check again before you decide.'
      : 'One moment.',
    whyExplanation: failed
      ? 'ORCA could not reach the forecast service, so it cannot judge conditions right now.'
      : '',
    evidenceChips: [],
    actionSteps: failed ? ['Check again before leaving.', 'Ask someone ashore for the local forecast.'] : [],
    warning: null,
    conditions: [],
    lastUpdated: failed ? 'unavailable' : 'checking…',
  };
}

export function pendingAlerts(base: AlertsPageData, failed: boolean): AlertsPageData {
  return {
    ...base,
    severity: 'none',
    mainAlert: null,
    activeAlerts: [],
    recentAlerts: [],
    noAlertsTitle: failed ? 'Alerts unavailable' : 'Checking for alerts…',
    noAlertsSubtitle: failed
      ? 'The forecast could not be reached. This is not an all-clear.'
      : 'Reading the latest forecast for your area.',
    whatShouldIDo: failed
      ? 'Check again before you leave. Do not treat this as a clear forecast.'
      : '',
  };
}

export function pendingSeaToday(base: SeaTodayData, failed: boolean): SeaTodayData {
  return {
    ...base,
    statusTitle: failed ? 'SEA STATE UNKNOWN' : 'CHECKING…',
    statusDescription: failed
      ? 'The forecast could not be loaded, so the sea state is unknown.'
      : 'Reading the latest forecast for your area.',
    conditions: [],
    forecast: [],
    updatedAgo: failed ? 'unavailable' : 'checking…',
  };
}

/** The agent's four-level verdict, mapped onto the Safety screen's three. */
export function toSafetyStatus(status: LiveConditions['safety']['status']): SafetyStatus {
  if (status === 'unsafe') return 'danger';
  if (status === 'caution') return 'caution';
  // "unknown" means the forecast is missing — treated as caution, never as safe.
  if (status === 'unknown') return 'caution';
  return 'safe';
}

export function toSeaStatus(status: LiveConditions['seaToday']['seaStatus']): SeaStatus {
  return status;
}

export function toAlertSeverity(alerts: LiveAlert[]): AlertSeverity {
  if (alerts.some((a) => a.severity === 'high')) return 'high';
  if (alerts.length > 0) return 'caution';
  return 'none';
}

const formatValue = (c: LiveCondition): string =>
  c.value == null ? '—' : `${c.value}${c.unit ? ` ${c.unit}` : ''}`;

/** Safety screen grades: good | neutral | warning | danger. */
const safetyStatusType = (t: LiveCondition['statusType']): ConditionItem['statusType'] =>
  t === 'alert' ? 'danger' : t === 'caution' ? 'warning' : 'good';

const conditionLabel = (c: LiveCondition): string => {
  if (c.statusType === 'alert') return 'Dangerous';
  if (c.statusType === 'caution') return 'Watch out';
  return 'Good';
};

/** Replace the Safety screen's facts with live ones, keeping translated copy. */
export function applySafetyLive(base: SafetyData, live: LiveConditions): SafetyData {
  const s = live.safety;

  const conditions: ConditionItem[] = s.conditions.map((c) => ({
    id: c.id,
    name: c.name,
    value: formatValue(c),
    status: conditionLabel(c),
    statusType: safetyStatusType(c.statusType),
    iconType: c.icon,
    note: c.note ?? undefined,
  }));

  // Evidence chips read straight off the measurements, so the reasons shown
  // are the numbers the verdict was actually computed from.
  const evidenceChips = s.conditions
    .filter((c) => c.value != null)
    .map((c) => `${c.statusType === 'good' ? '✓' : '⚠️'} ${c.name} ${formatValue(c)}`);

  const warning =
    live.alerts.length > 0
      ? {
          title: live.alerts[0].title,
          summary: live.alerts[0].message,
          advisory: live.alerts[0].actionRequired ?? '',
          activeFrom: clockTime(live.alerts[0].startsAt),
        }
      : null;

  const why = s.reasons.length
    ? s.reasons.join('; ')
    : base.whyExplanation;

  const safeUntilNote = s.safeUntil
    ? `Conditions hold until ${clockTime(s.safeUntil)}, then ${s.safeUntilReasons.join(', ')}.`
    : '';

  return {
    ...base,
    status: toSafetyStatus(s.status),
    whyExplanation: safeUntilNote ? `${why}. ${safeUntilNote}` : why,
    evidenceChips: evidenceChips.length ? evidenceChips : base.evidenceChips,
    actionSteps: s.adviceSteps.length ? s.adviceSteps : base.actionSteps,
    warning,
    conditions,
    lastUpdated: relativeTime(live.fetchedAt),
  };
}

const seaStatusType = (t: LiveCondition['statusType']): SeaTodayCondition['statusType'] => t;

/** Replace the Sea Today screen's facts with live ones. */
export function applySeaTodayLive(base: SeaTodayData, live: LiveConditions): SeaTodayData {
  const sea = live.seaToday;

  const conditions: SeaTodayCondition[] = sea.conditions.map((c) => ({
    id: c.id,
    name: c.name,
    value: c.value == null ? '—' : String(c.value),
    unit: c.unit,
    status: conditionLabel(c),
    statusType: seaStatusType(c.statusType),
    icon: c.icon,
  }));

  // Every third hour keeps the strip readable while still covering the day.
  const forecast: ForecastHour[] = sea.forecast
    .filter((_, i) => i % 3 === 0)
    .slice(0, 6)
    .map((h) => ({
      time: clockTime(h.time),
      icon:
        h.condition === 'Thunderstorm'
          ? '⛈️'
          : h.condition === 'Fog'
            ? '🌫️'
            : h.condition.includes('shower') || h.condition === 'Rain'
              ? '🌧️'
              : h.condition === 'Drizzle'
                ? '🌦️'
                : h.condition === 'Cloudy'
                  ? '☁️'
                  : h.condition === 'Partly cloudy'
                    ? '⛅'
                    : '☀️',
      temp: h.temp == null ? '—' : `${h.temp}°`,
      condition: h.condition,
    }));

  return {
    ...base,
    seaStatus: toSeaStatus(sea.seaStatus),
    statusDescription: sea.description,
    updatedAgo: relativeTime(live.fetchedAt),
    conditions,
    forecast: forecast.length ? forecast : base.forecast,
    advice: {
      ...base.advice,
      quote: live.safety.reasons.length ? live.safety.reasons.join('; ') : base.advice.quote,
      type:
        live.safety.status === 'unsafe'
          ? 'danger'
          : live.safety.status === 'safe'
            ? 'good'
            : 'caution',
    },
  };
}

const toAlertItem = (a: LiveAlert): AlertItem => ({
  id: a.id,
  severity: a.severity === 'high' ? 'high' : 'caution',
  badgeLabel: a.badgeLabel,
  title: a.title,
  message: a.message,
  timeAgo: `from ${clockTime(a.startsAt)}`,
  actionRequired: a.actionRequired,
});

/** Replace the Alerts screen's contents with alerts derived from the forecast. */
export function applyAlertsLive(base: AlertsPageData, live: LiveConditions): AlertsPageData {
  const alerts = live.alerts.map(toAlertItem);

  return {
    ...base,
    severity: toAlertSeverity(live.alerts),
    mainAlert: alerts[0] ?? null,
    activeAlerts: alerts,
    // There is no alert history feed yet, so this is empty rather than filled
    // with invented past warnings.
    recentAlerts: [],
    whatShouldIDo: live.safety.adviceSteps.join(' '),
  };
}
