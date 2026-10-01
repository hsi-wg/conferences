```{=html}
<div class="quarto-listing-container-custom">
  <div class="list quarto-listing-default">
    <% for (const item of items) { %>
    <article class="quarto-posts-default" <%= metadataAttrs(item) %>>
      <h3 class="listing-title">
        <a href="<%- item.path %>"><%- item.title %></a>
      </h3>
      <% if (item.authors) { %>
      <p class="listing-authors">
        <strong>Authors:</strong>
        <%= item.authors.map((author) => typeof author === 'string' ? author : author.name).join(', ') %>
      </p>
      <% } %>
      <% if (item.doi) { %>
      <p class="listing-doi">
        <strong>DOI:</strong>
        <a href="https://doi.org/<%- item.doi.replace(/^https:\/\/doi\.org\//, '') %>"><%- item.doi.replace(/^https:\/\/doi\.org\//, '') %></a>
      </p>
      <% } %>
      <% if (item.abstract) { %>
      <p class="listing-abstract"><%- item.abstract %></p>
      <% } %>
    </article>
    <% } %>
  </div>
</div>
```
