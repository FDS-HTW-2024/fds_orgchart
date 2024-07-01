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
        firstBtn.classList.remove("tab_active")
        firstBtn.classList.add("tab")
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

        secondBtn.classList.remove("tab")
        secondBtn.classList.add("tab_active")

        console.log(secondBtn.classList)
        document.getElementById('svgContainer').innerHTML = '';
        fetch('data.json')
        .then(response => response.json())
        .then(data => {
            createSVG(data, 2);
        })
        .catch(error => console.error('Error fetching JSON:', error));
    });
    thirdBtn.addEventListener('click', function() {

        secondBtn.classList.remove("tab_active")
        secondBtn.classList.add("tab")

        thirdBtn.classList.remove("tab")
        thirdBtn.classList.add("tab_active")

        console.log(secondBtn.classList)
        console.log(thirdBtn.classList)

        document.getElementById('svgContainer').innerHTML = '';
        fetch('data.json')
        .then(response => response.json())
        .then(data => {
            createSVG(data, 3);
        })
        .catch(error => console.error('Error fetching JSON:', error));
    });
});

function createSVG(data, identifier) {
    const svgNamespace = "http://www.w3.org/2000/svg";
    const svgContainer = document.getElementById('svgContainer');


    // Create an SVG element
    const svg = document.createElementNS(svgNamespace, 'svg');
    svg.setAttribute('width', '400');
    svg.setAttribute('height', '400');
    svg.setAttribute('viewBox', '0 0 400 400');

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
    }

    // Append the SVG to the container
    svgContainer.appendChild(svg);
}

