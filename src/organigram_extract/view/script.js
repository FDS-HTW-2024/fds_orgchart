function createTabs(){
    document.addEventListener("DOMContentLoaded", function(){
        try{
            let result;
            fetch('data.json')
            .then(response => response.json())
            .then(data => {
                console.log(data);
                result = countFileNameOccurrences(data);
                const tabsContainer = document.getElementById("tabsContainer");
                const timelineElement = document.querySelector(".timeline-ul");
            
                for(let j = 0; j < result.count; j++){
                    let newTab = document.createElement("button");
                    newTab.classList.add("tab");
                    newTab.setAttribute('id',j);
                    getTabName(newTab, result.values[j])
                    newTab.id

                    if(Number(newTab.id)=== 0){
                        newTab.classList.add("tab_active");
                    }

                    newTab.addEventListener("click", function(){
                        document.querySelectorAll('.tab').forEach(tab => tab.classList.remove("tab_active"));
                        newTab.classList.add("tab_active");
                    });

                    tabsContainer.appendChild(newTab);
                    createSVG(data, j);
                    drawTimeLineNode(data, timelineElement, j);
                }

                
            })
        } catch (error){
            (console.error('Error fetching JSON:', error));
        }
    })
}

function getTabName(newTab, nameParameter){
    document.getElementById('svgContainer').innerHTML = '';
    tabName = nameParameter;
    newTab.innerHTML = tabName;
};

function drawTimeLineNode(data, timelineElement, numberOfElements){
    const timelineItem = document.createElement("li");
    timelineItem.classList.add("active-timeline");
    const dateSpan = document.createElement("span");
    const dateDiv = document.createElement("div");
    dateDiv.textContent = data[numberOfElements].date;
    timelineItem.appendChild(dateSpan);
    timelineItem.appendChild(dateDiv);
    timelineElement.appendChild(timelineItem);
}

function countFileNameOccurrences(obj) {
    let count = 0;
    let values = [];

    function recursiveSearch(currentObj) {
        for (const key in currentObj) {
            if (currentObj.hasOwnProperty(key)) {
                const value = currentObj[key];
                if (key === "fileName") {
                    count++;
                    values.push(value);
                }
                if (typeof value === 'object' && value !== null) {
                    recursiveSearch(value);
                }
            }
        }
    }

    recursiveSearch(obj);

    return { count, values };
}

function createSVG(data, identifier) {
    const svgNamespace = "http://www.w3.org/2000/svg";
    const svgContainer = document.getElementById('svgContainer');

    // Create an SVG element
    const svg = document.createElementNS(svgNamespace, 'svg');
    svg.setAttribute('width', '1200');
    svg.setAttribute('height', '600');
    svg.setAttribute('viewBox', '0 0 1200 600');

    // Example: Create rects from JSON data
    data[identifier].content.forEach(item => {
        const bbox = item.bbox;
        const rect = document.createElementNS(svgNamespace, 'rect');
        rect.setAttribute('x', bbox[0]);
        rect.setAttribute('y', bbox[1]);
        rect.setAttribute('width', bbox[2] - bbox[0]);
        rect.setAttribute('height', bbox[3] - bbox[1]);
        rect.setAttribute('stroke', "black")
        rect.setAttribute('fill', "white")
        rect.setAttribute('stroke-width', 1)
        svg.appendChild(rect);
    })

    // Append the SVG to the container
    svgContainer.appendChild(svg);
}

/*Could be useful later?

function formatDate(dateString) {
    const [day, month, year] = dateString.split('.');
    return '${day}.${month}.${year}';    
}
*/

createTabs();


