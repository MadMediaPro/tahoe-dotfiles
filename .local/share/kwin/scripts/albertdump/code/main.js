function dump(w) {
  var o = {
    caption: w.caption, resourceClass: w.resourceClass, resourceName: w.resourceName,
    windowRole: w.windowRole, normalWindow: w.normalWindow, dialog: w.dialog,
    popup: w.popup, popupMenu: w.popupMenu, dropdownMenu: w.dropdownMenu,
    menu: w.menu, tooltip: w.tooltip, notification: w.notification,
    onScreenDisplay: w.onScreenDisplay, utility: w.utility, splash: w.splash,
    desktopWindow: w.desktopWindow, dock: w.dock, toolbar: w.toolbar,
    comboBox: w.comboBox, keepAbove: w.keepAbove, noBorder: w.noBorder,
    opacity: w.opacity, frameGeometry: "" + w.frameGeometry
  };
  print("ALBERTDUMP " + JSON.stringify(o));
}
var wins = workspace.windowList();
for (var i = 0; i < wins.length; i++) {
  var w = wins[i];
  var s = ((w.resourceClass || "") + " " + (w.resourceName || "") + " " + (w.caption || "")).toLowerCase();
  if (s.indexOf("albert") >= 0) dump(w);
}
