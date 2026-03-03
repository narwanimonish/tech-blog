# Tech-Blog

Users (GET/PUT/DEL) - Simple just do store users in DDB
Posts (GET/POST/PUT/DEL) - Simple just do store posts in DDB

Registration & Login - through Cognito

Lambda authorizer
1. just validates user token
2. validates roles

Users:GET, Users:PUT, Users:DEL, posts:POST, posts:PUT, posts:DEL - allowed to admins
(own id) Users:GET, Users:PUT, Users:DEL - allowed to that user
Post:GET - all

User, Admin, Guest