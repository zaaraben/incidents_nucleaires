/* global ol, CustomLayer */

var layerid = "sites_nucleaires";

function siteStyleFn() {
  return new ol.style.Style({
    image: new ol.style.Circle({
      radius: 6,
      fill: new ol.style.Fill({ color: "rgba(0,0,0,0.9)" }),
      stroke: new ol.style.Stroke({ color: "rgba(255,255,255,0.9)", width: 2 })
    })
  });
}

var layer = new ol.layer.Vector({
  source: new ol.source.Vector({
    url: "apps/incidents_nucleaires/data/sites.geojson",
    format: new ol.format.GeoJSON({
      dataProjection: "EPSG:4326",
      featureProjection: "EPSG:3857"
    })
  }),
  style: siteStyleFn
});

// IMPORTANT : zIndex bas (dessous)
layer.setZIndex(10);

new CustomLayer(layerid, layer);
