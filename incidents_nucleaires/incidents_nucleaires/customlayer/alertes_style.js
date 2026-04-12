/* global ol, CustomLayer */

var layerid = "alertes_2025";

function colorByINES(ines) {
  var v = (ines === null || ines === undefined || ines === "") ? null : Number(ines);
  if (v === null || isNaN(v)) return "rgba(130,130,130,0.85)"; // NC
  if (v <= 0) return "rgba(241,245,248,1)";
  if (v === 1) return "rgba(169,138,54,1)";
  if (v === 2) return "rgb(74,66, 128)";
  if (v === 3) return "rgba(113,147,188,1)";
  if (v === 4) return "rgba(8,109,8,1)";
  if (v === 5) return "rgba(141,185,89,1)";
  if (v === 6) return "rgba(230,166,79,1)";
  if (v === 7) return "rgba(152,42,57,1)";
  return "rgba(220,20,60,0.85)"; // 4+
}

function alertStyleFn(feature) {
  var ines = feature.get("niveau_ines");
  var fill = colorByINES(ines);

  var statut = (feature.get("statut") || "").toLowerCase();
  var dateFin = feature.get("date_fin"); // null si en cours
  var isOpen = (statut.indexOf("en cours") !== -1) || (dateFin === null);

  var radius = isOpen ? 12 : 10;

  return new ol.style.Style({
    image: new ol.style.RegularShape({
      points: 3,
      radius: radius,
      rotation: 0,
      fill: new ol.style.Fill({ color: fill }),
      stroke: new ol.style.Stroke({ color: "rgba(0,0,0,0.95)", width: 2 })
    })
  });
}

var layer = new ol.layer.Vector({
  source: new ol.source.Vector({
    url: "apps/incidents_nucleaires/data/alertes_2025.geojson",
    format: new ol.format.GeoJSON({
      dataProjection: "EPSG:4326",
      featureProjection: "EPSG:3857"
    })
  }),
  style: alertStyleFn
});

// IMPORTANT : zIndex haut (au-dessus des sites)
layer.setZIndex(100);

new CustomLayer(layerid, layer);
