document.addEventListener('DOMContentLoaded', function () {
    fetch('data.json')
        .then(response => response.json())
        .then(data => {
            createSVG(data);
        })
        .catch(error => console.error('Error fetching JSON:', error));
});

function createSVG(data) {
    const svgNamespace = "http://www.w3.org/2000/svg";
    const svgContainer = document.getElementById('svgContainer');

    // Create an SVG element
    const svg = document.createElementNS(svgNamespace, 'svg');
    svg.setAttribute('width', '500');
    svg.setAttribute('height', '500');
    svg.setAttribute('viewBox', '0 0 500 500');

    // Example: Create circles from JSON data
    data.circles.forEach(circle => {
        const circleElement = document.createElementNS(svgNamespace, 'circle');
        circleElement.setAttribute('cx', circle.cx);
        circleElement.setAttribute('cy', circle.cy);
        circleElement.setAttribute('r', circle.r);
        circleElement.setAttribute('fill', circle.fill);
        svg.appendChild(circleElement);
    });

    // Append the SVG to the container
    svgContainer.appendChild(svg);
}

