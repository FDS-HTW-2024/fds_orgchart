document.addEventListener('DOMContentLoaded', function () {
    fetch('data.json')
        .then(response => response.json())
        .then(data => {
            createSVG(data);
        })
        .catch(error => console.error('Error fetching JSON:', error));

    const firstBtn = document.getElementById('first');
    const secondBtn = document.getElementById('second');
    const thirdBtn = document.getElementById('third');

    firstBtn.addEventListener('click', function() {

        firstBtn.classList.add("tab_active")
        firstBtn.classList.remove("tab")

        secondBtn.classList.remove("tab_active")
        secondBtn.classList.add("tab")

        thirdBtn.classList.remove("tab_active")
        thirdBtn.classList.add("tab")

        document.getElementById('svgContainer').innerHTML = '';
        fetch('data.json')
        .then(response => response.json())
        .then(data => {
            createSVG(data, 1);
        })
        .catch(error => console.error('Error fetching JSON:', error));
    });

    secondBtn.addEventListener('click', function() {

        firstBtn.classList.remove("tab_active")
        firstBtn.classList.add("tab")

        thirdBtn.classList.remove("tab_active")
        thirdBtn.classList.add("tab")

        secondBtn.classList.remove("tab")
        secondBtn.classList.add("tab_active")

        document.getElementById('svgContainer').innerHTML = '';
        fetch('data.json')
        .then(response => response.json())
        .then(data => {
            createSVG(data, 2);
        })
        .catch(error => console.error('Error fetching JSON:', error));
    });
    thirdBtn.addEventListener('click', function() {

        firstBtn.classList.remove("tab_active")
        firstBtn.classList.add("tab")

        secondBtn.classList.remove("tab_active")
        secondBtn.classList.add("tab")

        thirdBtn.classList.remove("tab")
        thirdBtn.classList.add("tab_active")

        document.getElementById('svgContainer').innerHTML = '';
        fetch('data.json')
        .then(response => response.json())
        .then(data => {
            createSVG(data, 4);
        })
        .catch(error => console.error('Error fetching JSON:', error));
    });
});

function createSVG(data, identifier) {
    const svgNamespace = "http://www.w3.org/2000/svg";
    const svgContainer = document.getElementById('svgContainer');


    // Create an SVG element
    const svg = document.createElementNS(svgNamespace, 'svg');
    svg.setAttribute('width', '1200');
    svg.setAttribute('height', '600');
    svg.setAttribute('viewBox', '0 0 600 1200');

    // Example: Create circles from JSON data
    if(identifier == 1){
        data.circles1.forEach(circle => {
            const circleElement = document.createElementNS(svgNamespace, 'circle');
            circleElement.setAttribute('cx', circle.cx);
            circleElement.setAttribute('cy', circle.cy);
            circleElement.setAttribute('r', circle.r);
            circleElement.setAttribute('fill', circle.fill);
            svg.appendChild(circleElement);
        });
    } else if(identifier == 2){
        data.circles2.forEach(circle => {
            const circleElement = document.createElementNS(svgNamespace, 'circle');
            circleElement.setAttribute('cx', circle.cx);
            circleElement.setAttribute('cy', circle.cy);
            circleElement.setAttribute('r', circle.r);
            circleElement.setAttribute('fill', circle.fill);
            svg.appendChild(circleElement);
        });
    } else if(identifier == 3){
        data.circles3.forEach(circle => {
            const circleElement = document.createElementNS(svgNamespace, 'circle');
            circleElement.setAttribute('cx', circle.cx);
            circleElement.setAttribute('cy', circle.cy);
            circleElement.setAttribute('r', circle.r);
            circleElement.setAttribute('fill', circle.fill);
            svg.appendChild(circleElement);
        });
    } else if(identifier == 4){
        data.rectangles1.forEach(rect => {
            const rectElement = document.createElementNS(svgNamespace, 'rect');
            const text = document.createElementNS(svgNamespace, 'text') 
            const textX = rect.x + Math.abs(rect.x - rect.x2)/2;
            const textY = rect.y + Math.abs(rect.y - rect.y2)/2;
            rectElement.setAttribute('x', rect.x);
            rectElement.setAttribute('y', rect.y);
            rectElement.setAttribute('width', Math.abs(rect.x - rect.x2));
            rectElement.setAttribute('height', Math.abs(rect.y - rect.y2));
            rectElement.setAttribute('fill', rect.fill)
            rectElement.setAttribute('stroke', "black")
            rectElement.setAttribute('stroke-width', 3)
            text.setAttribute('x', textX)
            text.setAttribute('y', textY)
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('dominant-baseline', 'middle');
            text.textContent = rect.text; 
            svg.appendChild(rectElement)
            svg.appendChild(text) 
        })

        data.lines1.forEach(line => {
            const lineElement = document.createElementNS(svgNamespace, 'line')
            lineElement.setAttribute('x1', line.x)
            lineElement.setAttribute('y1', line.y)
            lineElement.setAttribute('x2', line.x2)
            lineElement.setAttribute('y2', line.y2)
            lineElement.setAttribute('stroke', 'black')
            lineElement.setAttribute('stroke-width', 2)
            svg.appendChild(lineElement)
        })

    }

    // Append the SVG to the container
    svgContainer.appendChild(svg);
}

