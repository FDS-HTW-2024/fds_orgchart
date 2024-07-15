function createTabs(){
    document.addEventListener("DOMContentLoaded", function(){

        let result;
        fetch('data.json')
        .then(response => response.json())
        .then(data => {
            result = countFileNameOccurrences(data);
            console.log(result.values[0])
            const tabsContainer = document.getElementById("tabsContainer");
        
            for(let i = 0; i < result.count; i++){
                let newTab = document.createElement("button");
                newTab.classList.add("tab");
                newTab.setAttribute('id',i);
                getTabName(newTab, result.values[i])
                newTab.id
                if(Number(newTab.id)=== 0){
                    newTab.classList.add("tab_active");
                }
                console.log(result.values[0])
                newTab.addEventListener("click", function(){
                    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove("tab_active"));
                    newTab.classList.add("tab_active");
                });

                tabsContainer.appendChild(newTab);
                createSVG(data, i);
            }
        })
        .catch(error => console.error('Error fetching JSON:', error));
    })
}

function getTabName(newTab, nameParameter){
    document.getElementById('svgContainer').innerHTML = '';
    tabName = nameParameter;
    newTab.innerHTML = tabName;
};

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

/*document.addEventListener('DOMContentLoaded', function() {
    const tabs = document.querySelectorAll('.tab');
    const root = document.documentElement;

    tabs.forEach((tab, index) => {
        const dateStr = tab.getAttribute('data-date');
        if (dateStr) {
            const [day, month, year] = dateStr.split('.');
            root.style.setProperty(`--year-${index}`, `'${year}'`);
        }
    });
});*/

function createSVG(data, identifier) {
    const svgNamespace = "http://www.w3.org/2000/svg";
    const svgContainer = document.getElementById('svgContainer');

    // Create an SVG element
    const svg = document.createElementNS(svgNamespace, 'svg');
    svg.setAttribute('width', '1200');
    svg.setAttribute('height', '600');
    svg.setAttribute('viewBox', '0 0 1200 600');

    // Example: Create circles from JSON data
    if(identifier == 0){
        data.content.forEach(item => {
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
    }

    // Append the SVG to the container
    svgContainer.appendChild(svg);
}

createTabs();


