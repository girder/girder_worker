document.addEventListener("DOMContentLoaded", function() {
    var width = 700,
        height = 350;

    var force = d3.layout.force()
            .charge(-120)
            .linkDistance(30)
            .size([width, height]);

    var svg = d3.select("#popularity-graph").append("svg")
            .attr("width", width)
            .attr("height", height);

    d3.json("_static/facebook-data.json", function(error, graph) {
        if (error) throw error;

        force
            .nodes(graph.nodes)
            .links(graph.links)
            .start();

        var link = svg.selectAll(".link")
                .data(graph.links)
                .enter().append("line")
                .attr("class", "link")
                .style("stroke-width", function(d) { return 1; });

        var node = svg.selectAll(".node")
                .data(graph.nodes)
                .enter().append("circle")
                .attr("class", "node")
                .attr("r", 5)
                .style("fill", "#1f77b4")
                .call(force.drag);

        node.append("title")
            .text(function(d) { return d.id; });

        force.on("tick", function() {
            link.attr("x1", function(d) { return d.source.x; })
                .attr("y1", function(d) { return d.source.y; })
                .attr("x2", function(d) { return d.target.x; })
                .attr("y2", function(d) { return d.target.y; });

            node.attr("cx", function(d) { return d.x; })
                .attr("cy", function(d) { return d.y; });
        });
    });
});
