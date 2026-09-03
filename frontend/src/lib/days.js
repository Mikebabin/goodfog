/** Group snapshot windows by day for the tab strip: [{day, label, am, pm}] in day order. Pure. */
export function groupByDay(windows) {
  const groups = [];
  for (const w of windows) {
    let g = groups.find((x) => x.day === w.day);
    if (!g) {
      g = { day: w.day, label: w.day_label ?? w.tab ?? '', am: null, pm: null };
      groups.push(g);
    }
    if (w.sun_label === 'Sunrise') g.am = w;
    else g.pm = w;
  }
  return groups;
}

/** Window to show when a day is picked: keep the current half if that day has it, else the half it has (sunset first). */
export function windowForDay(group, current) {
  const wantAm = current?.sun_label === 'Sunrise';
  return (wantAm ? group.am : group.pm) ?? group.pm ?? group.am;
}

/** Tab strip id for a day group. */
export const dayTabId = (day) => `day${day}`;

/** Tab strip entries: one per day group plus Plan. */
export function tabsFor(groups) {
  return [...groups.map((g) => ({ id: dayTabId(g.day), label: g.label })), { id: 'plan', label: '🔭 Plan' }];
}

/** The day group a tab id names, or null for 'plan' / unknown ids. */
export function groupForTabId(groups, id) {
  return groups.find((g) => dayTabId(g.day) === id) ?? null;
}
