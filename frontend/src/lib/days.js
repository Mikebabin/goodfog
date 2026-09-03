/** Group snapshot windows by day for the tab strip: [{day, label, am, pm}] in day order. Pure. */
export function groupByDay(windows) {
  const groups = [];
  for (const w of windows) {
    let g = groups.find((x) => x.day === w.day);
    if (!g) {
      g = { day: w.day, label: w.day_label, am: null, pm: null };
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
