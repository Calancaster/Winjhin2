const loader = document.querySelectorAll("#loader path");

for (let i = 0; i < loader.length; i++) {
    console.log(`Letter ${i} is ${loader[i].getTotalLength()}`);
}

const logo = document.querySelectorAll("#loading-blossom path");

for (let i = 0; i < logo.length; i++) {
    console.log(`Leaf ${i} is ${logo[i].getTotalLength()}`);
}