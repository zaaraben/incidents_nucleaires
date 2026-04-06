/* global ol */

function colorByINES(ines) {
  var v = (ines === null || ines === undefined || ines === "") ? null : Number(ines);
  if (v === null || isNaN(v)) return "rgba(130,130,130,0.85)";
  if (v <= 0) return "rgba(90,90,90,0.85)";
  if (v === 1) return "rgba(30,144,255,0.85)";
  if (v === 2) return "rgba(255,165,0,0.85)";
  if (v === 3) return "rgba(255,99,71,0.85)";
  return "rgba(220,20,60,0.85)";
}

function triangleStyle(fillColor, radius) {
  return new ol.style.Style({
    image: new ol.style.RegularShape({
      points: 3,
      radius: radius,
      rotation: 0,
      fill: new ol.style.Fill({ color: fillColor }),
      stroke: new ol.style.Stroke({ color: "rgba(0,0,0,0.95)", width: 2 })
    })
  });
}

function styleFn(feature) {
  var p = feature.getProperties ? feature.getProperties() : {};
  var fill = colorByINES(p.niveau_ines);

  var statut = (p.statut || "").toLowerCase();
  var isOpen = (statut.indexOf("en cours") !== -1) || (p.date_fin === null);

  var radius = isOpen ? 16 : 10;
  return triangleStyle(fill, radius);
}

var style = styleFn;
